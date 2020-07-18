# -*- coding: utf-8 -*-
import datetime
import json

import requests
import time
from fastapi import FastAPI, File, Header, Form
from src import manageUser
from starlette.middleware.cors import CORSMiddleware
from src.manageUser import ManageUser
from src import util
from models import dbconn
from pydantic import BaseModel
from starlette.responses import Response
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from src.util import Util
from models.helper import Helper

# manageUserClass = ManageUser()
dbClass = Helper(init=True)
utilClass = Util()

app = FastAPI(openapi_url="/api/v1/openapi.json", docs_url="/docs", redoc_url=None)
# app.include_router(getObject.router)
# app.include_router(labelRouter.router)
# app.include_router(fileRouter.router)
# app.include_router(predictRouter.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
def shutdown_event():

    if not dbconn.is_closed():
        dbconn.close()

@app.get("/")
def getRoot(response: Response):
    response.status_code = HTTP_200_OK
    return

class UserInfo(BaseModel):
    email: str
    password: str
    repeatpassword: str = None
    firstname: str = None
    name: str = None

@app.post("/register/")
def register(response: Response, email: str = Form(...), password : str = Form(...), repeatpassword: str = Form(...), firstname: str = Form(...), name: str = Form(...)):

    userInfo = {
        "email" : email,
        "password" : password,
        "repeatpassword": repeatpassword,
        "firstname": firstname,
        "name": name
    }

    if userInfo.birth:
        userInfo.birth = datetime.datetime.strptime(userInfo.birth, "%Y-%m-%dT%H:%M:%S")

    response.status_code, result = manageUser.ManageUser().registerUser(userInfo)

    return result

class UserLoginInfo(BaseModel):
    identifier: str
    password: str

@app.post("/login/")
def login(userLoginInfo: UserLoginInfo, response: Response):

    response.status_code, result = manageUser.ManageUser().loginUser(userLoginInfo)

    return result

class UserEmailInfo(BaseModel):
    email: str

@app.post("/forgot-password/")
def forgotPassword(userEmailInfo: UserEmailInfo, response: Response):

    response.status_code, result = manageUser.ManageUser().forgotPassword(userEmailInfo.email)

    return result

class ResetPasswordInfo(BaseModel):
    code: str
    password: str
    passwordConfirmation: str

@app.post("/reset-password/")
def resetPassword(resetPasswordInfo: ResetPasswordInfo, response: Response):

    response.status_code, result = manageUser.ManageUser().resetPassword(resetPasswordInfo.code, resetPasswordInfo.password, resetPasswordInfo.passwordConfirmation)

    return result

@app.get("/email-confirm/")
def EmailConfirm(token: str, user: str, response: Response):

    response.status_code, result = manageUser.ManageUser().verifyEmailConfirm(token, user)

    return result