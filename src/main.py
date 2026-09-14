from fastapi import FastAPI, Request
from enum import Enum
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app= FastAPI(title='Test1')


templates=Jinja2Templates(directory='../templates')

app.mount('/static',StaticFiles(directory='../static'),name='static')

@app.get('/')
def leer_index(request:Request):

    return templates.TemplateResponse(name='index.html',request=request)

@app.get('/contact')
def read_contact(request:Request):
    return templates.TemplateResponse(name='contact.html',request=request)





