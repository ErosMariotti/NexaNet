import os
from bose import *
from bose.utils import merge_dicts_in_one_dict, remove_nones
import selenium
from selenium.common.exceptions import JavascriptException
import re

class ScrapeGoogleMapsPlacesTask(BaseTask):
    task_config = TaskConfig(output_filename="all", log_time=False, close_on_crash=True)

    browser_config = BrowserConfig(headless=True)

    def get_data(self):
        return LocalStorage.get_item('queries', [])

    def run(self, driver, data):
        links = data['links']
        query = data['query']

        def get_maps_data(links):

            def get_data(link):

                def get_heading_text(max_attempts):
                    for attempt in range(1, max_attempts + 1):
                        heading = driver.get_element_or_none_by_selector('h1', Wait.SHORT)

                        if heading is not None:
                            title = heading.text
                        else:
                            title = ''

                        if title == '':
                            if attempt < max_attempts:
                                print("Did Not Get Heading. Retrying ...", link)
                                driver.get(link)
                                driver.long_random_sleep()
                            else:
                                print("Failed to retrieve heading text after 5 attempts.")
                                print("Skipping...", link)
                        else:
                            return title

                    return ''

                driver.get_by_current_page_referrer(link)
                out_dict = {}
                title = get_heading_text(5)

                if not title:
                    print("Skipping (no title):", link)
                    return None

                out_dict = {
                    "title": title,
                    "link": link,
                }

                # ====== SCRIPT JS PARA LEER DATOS DEL DOM ======
                js_code = """
                function firstText(selectors) {
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && (el.innerText || el.textContent)) {
                            return (el.innerText || el.textContent).trim();
                        }
                    }
                    return null;
                }

                function firstHref(selectors) {
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.href) {
                            return el.href;
                        }
                    }
                    return null;
                }

                // Dirección (ya la estamos sacando bien, pero la leemos igual por si acaso)
                const address = firstText([
                    '[data-item-id="address"]',
                    'button[data-item-id="address"]',
                    'button[aria-label*="dirección"]'
                ]);

                // Teléfono
                const phone = firstText([
                    '[data-item-id^="phone:"]',
                    'button[data-item-id^="phone:"]',
                    'button[aria-label^="+"]',
                    'button[aria-label*="teléfono"]'
                ]);

                // Sitio web
                const website = firstHref([
                    'a[data-item-id="authority-url"]',
                    'a[data-item-id="authority"]',
                    'a[aria-label*="Sitio web"]',
                    'a[data-tooltip*="Sitio web"]'
                ]);

                // Categoría (Hotel, Hotel de 3 estrellas, etc.)
                const category = firstText([
                    'button[jsaction*="pane.rating.category"]',
                    'button[aria-label*="categoría"]'
                ]);
                

                // ===== NUEVA LÓGICA PARA RATING Y RESEÑAS =====
                let ratingLabel = null;
                let reviewsText = null;

                // Recorremos todos los <span> y buscamos:
                //  - un texto solo numérico tipo "4,3"  -> rating
                //  - un texto con "reseñas" u "opiniones" -> reviews
                const spans = Array.from(document.querySelectorAll('span'));
                for (const span of spans) {
                    const txt = (span.innerText || '').trim();
                    if (!txt) continue;

                    // Ej: "1.234 reseñas", "850 opiniones"
                    if (!reviewsText && (txt.toLowerCase().includes('reseñas') || txt.toLowerCase().includes('opiniones'))) {
                        reviewsText = txt;
                    }

                    // Ej: "4,3" solo como número de rating
                    if (!ratingLabel) {
                        const m = txt.match(/^(\d+[.,]\d+)\s*$/);
                        if (m) {
                            ratingLabel = txt;
                        }
                    }
                }

                return {
                    address,
                    phone,
                    website,
                    category,
                    ratingLabel,
                    reviewsText
                };
                """

                try:
                    additional = driver.execute_script(js_code)
                    print("JS result:", additional)
                except JavascriptException as e:
                    print(f"Error ejecutando JS en {link}: {e}")
                    additional = {}

                # ====== PROCESAR LO QUE VINO DEL JS ======

                # Dirección: limpiamos el iconito raro \ue0c8 y saltos de línea
                address = additional.get("address")
                if address:
                    address = address.replace('\ue0c8', '').strip()
                    out_dict["address"] = address

                # Teléfono
                phone = additional.get("phone")
                if phone:
                    phone = phone.replace('\ue0b0', '').strip()
                    out_dict["phone"] = phone

                # Sitio web
                website = additional.get("website")
                if website:
                    out_dict["website"] = website.strip()

                # Categoría principal
                category = additional.get("category")
                if category:
                    out_dict["main_category"] = category.strip()

                # Rating
                rating_label = additional.get("ratingLabel")
                if rating_label:
                    try:
                        # Ej: "4,3 de 5" -> "4,3" -> 4.3
                        num = rating_label.split(" ")[0].replace(",", ".")
                        out_dict["rating"] = float(num)
                    except Exception as e:
                        print("Error parseando rating:", rating_label, e)

                # Reseñas
                reviews_text = additional.get("reviewsText")
                if reviews_text:
                    try:
                        # Extraemos el número: "1.234 reseñas" -> 1234
                        m = re.search(r'\d[\d\.\,]*', reviews_text)
                        if m:
                            reviews_str = m.group(0).replace(".", "").replace(",", "")
                            out_dict["reviews"] = int(reviews_str)
                    except Exception as e:
                        print("Error parseando reviews:", reviews_text, e)

                print('Done:', out_dict.get('title', ''))
                return out_dict


            ls = remove_nones(list(map(get_data, links)))

            return ls

        driver.get_google()

        results = get_maps_data(links)

        return results
