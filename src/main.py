from fastapi import FastAPI, Request
from enum import Enum
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app= FastAPI(title='Test1')
templates=Jinja2Templates(directory='../templates')



@app.get('/',response_class=HTMLResponse)
def leer_index(request:Request):
    
    return templates.TemplateResponse(name='index.html',request=request)



