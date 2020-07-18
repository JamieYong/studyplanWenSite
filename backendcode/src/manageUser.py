import ast
import re
import time
import traceback
import uuid

import dateutil
import pandas as pd
import requests
import os
import json
import bcrypt
import jwt
from starlette.responses import RedirectResponse

from src.util import Util
from models.helper import Helper
import datetime
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_201_CREATED
from starlette.status import HTTP_301_MOVED_PERMANENTLY
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE
from starlette.status import HTTP_400_BAD_REQUEST
from starlette.status import HTTP_403_FORBIDDEN
from starlette.status import HTTP_423_LOCKED
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.status import HTTP_507_INSUFFICIENT_STORAGE
import urllib
import urllib.parse
from uuid import uuid4
#TODO: 숫자 헤더면 바꿔줘야됨
class ManageUser:

    def __init__(self):
        self.dbClass = Helper(init=True)
        self.utilClass = Util()
        self.paymentClass = ManagePayment()
        self.s3 = self.utilClass.getBotoClient('s3')
        self.invaildUserAuthResponse = {
                    "statusCode": 500,
                    "error": "Bad Request",
                    "message": "잘못된 접근입니다."
                }
        self.failUserAuthResponse = {
                    "statusCode": 500,
                    "error": "Bad Request",
                    "message": "유저 정보를 찾을 수 없습니다."
                }
        self.sendEmailAuthResponse = {
                    "statusCode": 200,
                    "message": "고객님의 메일로 링크를 보내드렸습니다. 메일발송까지 5-10분 정도 소요될 수 있습니다."
                }

    def registerUser(self, userInfoRaw):
        userInfo = userInfoRaw.__dict__
        salt = bcrypt.gensalt(10)

        if not re.match(r'[A-Za-z0-9!@#$%^&+=]{8,}', userInfo["password"]):
            return HTTP_500_INTERNAL_SERVER_ERROR, {
                "statusCode": 500,
                "error": "Bad Request",
                "message": "비밀번호가 양식에 맞지 않습니다. 다시 시도하여 주시길 바랍니다."
            }

        if len(re.findall("[a-z]", userInfo["password"])) == 0 or len(re.findall("[0-9]", userInfo["password"])) == 0 or len(re.findall("[!@#$%^&+=]",userInfo["password"])) == 0:
            return HTTP_500_INTERNAL_SERVER_ERROR, {
                "statusCode": 500,
                "error": "Bad Request",
                "message": "영어, 숫자, 특수기호가 최소 1개이상 포함되어야 합니다."
            }

        userInfo["password"] = bcrypt.hashpw(userInfo["password"].encode(), salt)
        try:
            userInfoRaw = self.dbClass.createUser(userInfo)
            userInfo = userInfoRaw.__dict__['__data__']
            del userInfo["password"]
        except:
            print(traceback.format_exc())
            return HTTP_400_BAD_REQUEST, {
                "statusCode": 400,
                "error": "Bad Request",
                "message": "이미 가입된 이메일입니다."
            }
            pass

            userInit = {
                "confirmed": True,
                "appTokenCode": uuid.uuid4().hex,
                "appTokenCodeUpdatedAt": datetime.datetime.utcnow(),
                'isFirstplanDone': True,
                'isDeleteRequested': 0,
                'usageplan': businessPlan["id"],
                'dynos': 1,
            }

        else:
            userInit = {
                 "confirmed": False,
                "emailTokenCode": uuid.uuid4().hex,
                "appTokenCode": uuid.uuid4().hex,
                "appTokenCodeUpdatedAt": datetime.datetime.utcnow(),
            }
        userInfo = {**userInfo, **userInit}

        self.dbClass.updateUser(userInfo['id'], userInit)
        return HTTP_201_CREATED, userInfo

    def loginUser(self, userLoginInfo):

        userInfo = {}

        try:
            userInfo['user'] = self.dbClass.loginUser(userLoginInfo.identifier, userLoginInfo.password).__dict__['__data__']
        except:
            pass

        if userInfo.get('user'):

            del userInfo['user']["password"]

            userInfo['jwt'] = userInfo['user']["token"]
            if not userInfo['user']["token"]:
                token = jwt.encode({'email': userInfo['user']["email"]}, 'aistorealwayswinning', algorithm='HS256')
                self.dbClass.updateUser(userInfo['user']["id"], {
                    'token': token
                })
                userInfo['jwt'] = token

            if userInfo['user']['confirmed'] and not userInfo['user']['isDeleteRequested']:
                self.utilClass.sendSlackMessage(f"로그인하였습니다. {userInfo['user']['email']} (ID: {userInfo['user']['id']})", appLog=True)
                return HTTP_200_OK, userInfo
            else:
                self.utilClass.sendSlackMessage(f"이메일 확인되지 않은 로그인 시도입니다. " + json.dumps(userLoginInfo.get('identifier'), indent=4, ensure_ascii=False),
                                                appLog=True)
                return HTTP_400_BAD_REQUEST, {
                    "status_code": 400,
                    "message": "Email verification is not confirmed."
                }
        else:
            self.utilClass.sendSlackMessage(f"로그인 시도 실패입니다. " + json.dumps(userLoginInfo.__dict__.get('identifier'), indent=4, ensure_ascii=False),
                                            appLog=True)
            return HTTP_400_BAD_REQUEST, userInfo

    def verifyEmailConfirm(self, token, userid):

        isVerified = self.dbClass.verifyEmailConfirm(token, userid)
        if isVerified:
            return HTTP_200_OK, RedirectResponse(url=self.utilClass.frontendURL + "/signin?email_confirm=true")
        else:
            return HTTP_503_SERVICE_UNAVAILABLE, RedirectResponse(
                url=self.utilClass.frontendURL + "/signin?email_confirm=false")

    def forgotPassword(self, email):
        try:
            user = self.dbClass.getUserByEmail(email)
        except:
            return HTTP_200_OK, self.sendEmailAuthResponse
            pass
        if user['isDeleteRequested']:
            return HTTP_500_INTERNAL_SERVER_ERROR, self.failUserAuthResponse

        with open("./src/email/password_reset.html", "r") as r:
            token = jwt.encode({'email': email + str(datetime.datetime.utcnow())}, 'aistorealwayswinning',
                               algorithm='HS256')
            print(token.decode())
            content = r.read().replace("<%= TOKEN %>", token.decode())
            result = self.utilClass.sendEmail(email, f'[Click AI] 비밀번호 리셋', content)
            self.dbClass.updateUser(user["id"], {
                "resetPasswordVerifyTokenID": token.decode(),
                "resetPasswordRequestDatetime": datetime.datetime.utcnow()
            })

    def resetPassword(self, token, password, passwordConfirmation):

        if password != passwordConfirmation:
            return HTTP_500_INTERNAL_SERVER_ERROR, {
                "statusCode": 500,
                "error": "Bad Request",
                "message": "비밀번호가 일치하지 않습니다. 다시 시도하여 주시길 바랍니다."
            }

        if not re.match(r'[A-Za-z0-9@#$%^&+=]{8,}', password):
            return HTTP_500_INTERNAL_SERVER_ERROR, {
                "statusCode": 500,
                "error": "Bad Request",
                "message": "비밀번호가 양식에 맞지 않습니다. 다시 시도하여 주시길 바랍니다."
            }
        if len(re.findall("[a-z]", password)) == 0 or len(re.findall("[0-9]", password)) == 0 or len(re.findall("[!@#$%^&+=]", password)) == 0:
            return HTTP_500_INTERNAL_SERVER_ERROR, {
                "statusCode": 500,
                "error": "Bad Request",
                "message": "영어, 숫자, 특수기호가 최소 1개이상 포함되어야 합니다."
            }

        try:
            user = self.dbClass.getUserByForgetEmailToken(token)
        except:
            return HTTP_500_INTERNAL_SERVER_ERROR, self.failUserAuthResponse
            pass
        if user["resetPasswordRequestDatetime"] + datetime.timedelta(days=1) < datetime.datetime.utcnow():
            return HTTP_500_INTERNAL_SERVER_ERROR, {
                    "statusCode": 500,
                    "error": "Bad Request",
                    "message": "갱신기한이 지났습니다. 비밀번호 찾기 페이지부터 다시 진행해주시길 바랍니다."
                }

        salt = bcrypt.gensalt(10)
        password = bcrypt.hashpw(password.encode(), salt)

        self.dbClass.updateUser(user["id"],{
            "password": password
        })

        self.utilClass.sendSlackMessage(f"비밀번호 리셋 완료합니다. {user['email']} (ID: {user['id']})", appLog=True)

        return HTTP_200_OK, {
            "statusCode": 200,
            "message": "비밀번호가 변경되었습니다. 다시 로그인해주시길 바랍니다."
        }