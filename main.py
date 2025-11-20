from bose.launch_tasks import launch_tasks
from bose import LocalStorage
from src import tasks_to_be_run

def print_pro_bot():
    global msg
    print(msg)

if __name__ == "__main__":
    import os
    from pathlib import Path
    import pandas as pd

    # 1) Ejecutar las tareas
    launch_tasks(*tasks_to_be_run)

    # 2) Unir todos los CSV en un solo Excel
    output_dir = Path("output")  # Bose suele usar esta carpeta por defecto
    all_csvs = list(output_dir.glob("*.csv"))

    all_dfs = []
    for csv_path in all_csvs:
        df = pd.read_csv(csv_path)
        # Opcional: agregar una columna con el nombre de la búsqueda
        df["keyword"] = csv_path.stem.replace("-", " ")
        all_dfs.append(df)

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_excel_path = output_dir / "resultados_completos.xlsx"
        final_df.to_excel(final_excel_path, index=False)
        print(f"Excel generado en: {final_excel_path}")
    else:
        print("No se encontró ningún CSV para unir.")

    # 3) (tu lógica original de LocalStorage si la usás)
    count = LocalStorage.get_item('count', 0)
    if count % 5 == 0:
        print_pro_bot()
