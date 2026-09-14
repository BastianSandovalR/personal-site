from fastapi import FastAPI, Request
from enum import Enum
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import random

app= FastAPI(title='Test1')


templates=Jinja2Templates(directory='../templates')

app.mount('/static',StaticFiles(directory='../static'),name='static')

@app.get('/',response_class=HTMLResponse)
def leer_index(request:Request):
    numero_aleatorio =random.randint(0,49)
    archivo=pd.read_json('data/citas.json')
    df=pd.DataFrame(archivo)
    #print (df)
    lista=[]
    #for linea in archivo:
       # print (linea)
    lista_filas=df.to_dict(orient='records')
    day_quote=lista_filas[numero_aleatorio]
    
    return templates.TemplateResponse(name='index.html',context={'request':request,'cita':day_quote})

@app.get('/contact')
def read_contact(request:Request):
    return templates.TemplateResponse(name='contact.html',request=request)


    




