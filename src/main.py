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
    user_agent=request.headers.get("user-agent")
    diccionario=dict(request.headers)
    print(diccionario['sec-ch-ua-mobile'][1])
    if diccionario['sec-ch-ua-mobile'][1]=='0':
        return templates.TemplateResponse(name='index_pc.html',context={'request':request,'cita':day_quote})
    else:
        return  templates.TemplateResponse(name='index_phone.html',context={'request':request,'cita':day_quote})

@app.get('/contact')
def read_contact(request:Request):
    return templates.TemplateResponse(name='contact.html',request=request)


    




