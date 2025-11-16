python -m venv env # Windows

env/scripts/activate

# instalar dependencias
pip install -r requirements.txt
# ejecutar la aplicación
uvicorn main:app --reload
