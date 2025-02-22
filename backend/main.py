from fastapi import FastAPI, UploadFile, File, Query
import pandas as pd
import io
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Permite requisições do frontend
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos os headers
)

# Criar um dicionário de categorias automáticas para os gastos
CATEGORIAS = {
    "alimentação": ["supermercado", "restaurante", "lanche", "mercado", "delivery"],
    "transporte": ["uber", "táxi", "ônibus", "alcool", "gasolina"],
    "saúde": ["farmácia", "remédio", "consulta", "exame"],
    "lazer": ["cinema", "show", "bar", "viagem", "games", "livros"],
    "moradia": ["aluguel", "condomínio", "luz", "água", "internet"],
}

df = None  # Variável global para armazenar o DataFrame

def categorizar_despesa(descricao):
    descricao = descricao.lower()
    for categoria, palavras in CATEGORIAS.items():
        if any(palavra in descricao for palavra in palavras):
                return categoria
    return "outros"

@app.get("/")
def home():
    return {"message": "API do Gerenciador de Gastos Funcionandos!"}

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...)):
    global df  # Referenciar a variável global df
    try:
        #Ler o arquivo CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        #KLinha para renomear as colunas
        df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]
        
        # Garantindo que a coluna "valor" seja numérica
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
        
        # Remover as linhas com valores vazios
        df.dropna(inplace=True)
        
        #Adicionando a categorização
        if "descricao" in df.columns:
            df["categoria"] = df["descricao"].apply(categorizar_despesa)
        
        return {
            "columns": df.columns.tolist(),
            "num_rows": len(df),
            "sample_data": df.head(5).to_dict(orient="records"),
            "message": "Arquivo processado com sucesso"
        }
        
    except Exception as e:
        return {"error" : str(e), "message": "Erro ao processar arquivo."}

@app.get("/resumo")
async def resumo_gastos(
    start_date: str = Query(..., description="Data inicial no formato YYYY-MM-DD"),
    end_date: str = Query(..., description="Data final no formato YYYY-MM-DD"),
):
    try:
        #Verifica se já existe um Dataframe carregado
        global df
        if df is None or df.empty:
            return {"error": "Nenhum arquivo CSV foi carregado ainda."}
        
        # Converter a coluna 'data" para datetime
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        
        #Converter as datas de início e fim
        start_date = pd.to_datetime(start_date, format="%Y-%m-%d")
        end_date = pd.to_datetime(end_date, format="%Y-%m-%d")
        
        #Filtrar as despesas dentro do período informado
        df_filtrado = df[(df["data"] >= start_date) & (df["data"] <= end_date)]
        
        #Agrupoar os valores por categoria e calcular o total
        resumo = df_filtrado.groupby("categoria")["valor"].sum().reset_index()
        
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "total_por_categoria": resumo.to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e), "message": "Erro ao gerar resumo de gastos."}
        
        