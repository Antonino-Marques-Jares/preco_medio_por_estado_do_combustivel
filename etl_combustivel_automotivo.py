"""
Mudança de preço do combustivel ao longo do tempo

Autor: Antonino Marques Jares
Fonte: https://dados.gov.br/dados/conjuntos-dados/serie-historica-de-precos-de-combustiveis-e-de-glp
Atualizado em: 03/11/2026

Pipeline: bronze -> prata -> SQLite -> JSON -> limpeza
"""

import json
import sqlite3
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Pastas de entrada/saída (ajuste se necessário)
DIR_BRONZE = Path(r"D:\ETL\nivel_01_bronze\combustiveis_automotivos")
DIR_PRATA  = Path(r"D:\ETL\nivel_02_prata\combustiveis_automotivos")

# Banco e JSON ficam ao lado do script
DB_PATH  = BASE_DIR / "combustiveis.db"
DIR_ETL  = BASE_DIR / "etl"
JSON_GLP = DIR_ETL / "combustiveis_automotivos.json"

# Nome único da tabela (evita divergência entre criação e escrita)
TABELA = "combustivel_automotivo"

# Processa de 2004 até 2026 (inclusive)
ANOS = list(range(2004, 2027))
SEMESTRES = ["01", "02"]

ANO_ATUAL = date.today().year

# Query central — usada tanto para gerar o JSON quanto para validar a limpeza
QUERY_AGREGADA = f"""
    SELECT
        ESTADO,
        PRODUTO,
        MES_ANO,
        AVG(VL_VENDA) AS VL_VENDA
    FROM {TABELA}
    WHERE MES_ANO IS NOT NULL
      AND VL_VENDA IS NOT NULL
      AND VL_VENDA > 0
    GROUP BY ESTADO, PRODUTO, MES_ANO
    ORDER BY ESTADO, PRODUTO, MES_ANO;
"""


# ---------------------------------------------------------------------------
# ETAPA 1 — bronze -> prata
# ---------------------------------------------------------------------------
def processar_bronze_para_prata() -> None:
    """Lê os CSVs brutos (bronze) e gera os CSVs tratados (prata)."""
    DIR_PRATA.mkdir(parents=True, exist_ok=True)

    colunas_necessarias = [
        "Regiao - Sigla", "Estado - Sigla", "Municipio",
        "CNPJ da Revenda", "Produto", "Data da Coleta", "Valor de Venda",
    ]

    for ano in ANOS:
        if ano > ANO_ATUAL:
            continue

        for semestre in SEMESTRES:
            planilha_origem  = DIR_BRONZE / f"ca-{ano}-{semestre}.csv"
            planilha_destino = DIR_PRATA  / f"ca-{ano}-{semestre}.csv"

            if not planilha_origem.exists():
                print(f"⚠ Arquivo não encontrado: {planilha_origem}")
                continue

            try:
                df = None
                for enc in ("utf-8", "latin1", "cp1252"):
                    try:
                        df = pd.read_csv(
                            planilha_origem, sep=";",
                            encoding=enc, low_memory=False,
                        )
                        break
                    except UnicodeDecodeError:
                        continue

                if df is None:
                    print(f"❌ Não foi possível decodificar {planilha_origem}")
                    continue

                faltantes = [c for c in colunas_necessarias if c not in df.columns]
                if faltantes:
                    print(f"⚠ Colunas faltantes em {planilha_origem}: {faltantes}")
                    continue

                df = df[colunas_necessarias].rename(columns={
                    "Estado - Sigla":  "ESTADO",
                    "Municipio":       "MUNICIPIO",
                    "CNPJ da Revenda": "CNPJ",
                    "Produto":         "PRODUTO",
                    "Data da Coleta":  "DATA",
                    "Valor de Venda":  "VL_VENDA",
                })

                df["DATA"]    = pd.to_datetime(df["DATA"], errors="coerce")
                df["ANO"]     = df["DATA"].dt.year.astype("Int64")
                df["MES"]     = df["DATA"].dt.month.astype("Int64")
                df["MES_ANO"] = (
                    df["MES"].astype(str).str.zfill(2)
                    + "/"
                    + df["ANO"].astype(str)
                )

                df.to_csv(planilha_destino, index=False, encoding="utf-8")
                print(f"✅ {planilha_destino} salvo com sucesso!")

            except Exception as e:
                print(f"❌ Erro grave em {planilha_origem}: {e}")

    print("✅ Todos os arquivos processados!")


# ---------------------------------------------------------------------------
# ETAPA 2 — prata -> SQLite
# ---------------------------------------------------------------------------
def _drop_tabela(cursor: sqlite3.Cursor) -> None:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {TABELA}")
    except Exception as e:
        print(f"Erro ao apagar tabela {TABELA}: {e}")


def _criar_tabela(cursor: sqlite3.Cursor) -> None:
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA} (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ESTADO     TEXT,
            PRODUTO    TEXT,
            MES_ANO    TEXT,
            VL_VENDA   REAL
        )
    """)


def carregar_prata_no_sqlite() -> None:
    """Lê os CSVs prata e popula a tabela no SQLite."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        _drop_tabela(cursor)
        _criar_tabela(cursor)
        conn.commit()

        for ano in ANOS:
            if ano > ANO_ATUAL:
                continue

            for semestre in SEMESTRES:
                print(f"\nProcessando ano ({ano}) / semestre ({semestre}) ...")
                arquivo = DIR_PRATA / f"ca-{ano}-{semestre}.csv"

                try:
                    df = pd.read_csv(
                        arquivo, sep=",", encoding="utf-8", low_memory=False,
                    )
                    df_filtrado = df[
                        ["ESTADO", "PRODUTO", "MES_ANO", "VL_VENDA"]
                    ].copy()

                    df_filtrado.to_sql(
                        name=TABELA, con=conn,
                        if_exists="append", index=False,
                    )
                    print(f"Dados de {ano} salvos.\nRegistros salvos: {len(df_filtrado)}")

                except FileNotFoundError:
                    print(
                        f"Arquivo do ano {ano} semestre {semestre} "
                        f"não encontrado. Pulando..."
                    )
                except Exception as e:
                    print(f"Erro ao processar {ano}/{semestre}: {e}")

        print("\nProcesso concluído com sucesso!")

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# ETAPA 3 — SQLite -> JSON
# ---------------------------------------------------------------------------
def gerar_json_combustiveis_automotivos() -> None:
    """Executa a query no SQLite e gera `etl/combustiveis_automotivos.json`."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(QUERY_AGREGADA, conn)
    finally:
        conn.close()

    # Garante tipos serializáveis em JSON
    df["ESTADO"]   = df["ESTADO"].astype(str)
    df["PRODUTO"]  = df["PRODUTO"].astype(str)
    df["MES_ANO"]  = df["MES_ANO"].astype(str)
    df["VL_VENDA"] = df["VL_VENDA"].astype(float).round(2)

    estrutura = {
        "metadados": {
            "data_de_atualizacao": date.today().strftime("%d-%m-%Y"),
            "responsavel":         "Antonino Marques Jares",
            "nome_programa":       "etl_combustivel_automotivo.py",
        },
        "dados": df.to_dict(orient="records"),
    }

    DIR_ETL.mkdir(parents=True, exist_ok=True)
    print(f"Salvando ... {JSON_GLP}")
    with open(JSON_GLP, "w", encoding="utf-8") as f:
        json.dump(estrutura, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON gerado com {len(df)} registros.")


# ---------------------------------------------------------------------------
# ETAPA 4 — limpeza de artefatos intermediários
# ---------------------------------------------------------------------------
def _json_valido_e_com_dados() -> bool:
    """Confere se o JSON existe, é legível e contém registros em 'dados'."""
    if not JSON_GLP.exists():
        return False
    try:
        with open(JSON_GLP, "r", encoding="utf-8") as f:
            conteudo = json.load(f)
        dados = conteudo.get("dados") or []
        if not dados:
            print("⚠ JSON existe, mas está vazio. Limpeza cancelada por segurança.")
            return False
        return True
    except Exception as e:
        print(f"⚠ JSON inválido ({e}). Limpeza cancelada por segurança.")
        return False


def limpar_artefatos_intermediarios() -> None:
    """Apaga CSVs da pasta prata e o banco SQLite após o JSON ser gerado."""
    if not _json_valido_e_com_dados():
        print(f"⚠ JSON não encontrado ou inválido ({JSON_GLP}). Limpeza cancelada.")
        return

    # 1. Apaga CSVs em DIR_PRATA
    if DIR_PRATA.exists():
        for csv in DIR_PRATA.glob("*.csv"):
            try:
                csv.unlink()
                print(f"🗑  Removido: {csv}")
            except Exception as e:
                print(f"⚠ Falha ao remover {csv}: {e}")
    else:
        print(f"⚠ Pasta não encontrada: {DIR_PRATA}")

    # 2. Apaga o banco SQLite
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
            print(f"🗑  Removido: {DB_PATH}")
        except Exception as e:
            print(f"⚠ Falha ao remover {DB_PATH}: {e}")
    else:
        print(f"⚠ Banco não encontrado: {DB_PATH}")

    print("✅ Limpeza concluída.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("ETAPA 1 — bronze -> prata")
    print("=" * 60)
    processar_bronze_para_prata()

    print("\n" + "=" * 60)
    print("ETAPA 2 — prata -> SQLite")
    print("=" * 60)
    carregar_prata_no_sqlite()

    print("\n" + "=" * 60)
    print("ETAPA 3 — SQLite -> JSON")
    print("=" * 60)
    gerar_json_combustiveis_automotivos()

    print("\n" + "=" * 60)
    print("ETAPA 4 — limpeza de artefatos intermediários")
    print("=" * 60)
    limpar_artefatos_intermediarios()


if __name__ == "__main__":
    main()