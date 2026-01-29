import copy
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Path, Query, Response, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator

import app_server.share.global_value as g
from app_server.database.db_config import DBConfig
from app_server.database.db_schema import Member
from app_server.model.token import Token
from app_server.repository.test_member_repository import MemberRepository
from app_server.service.auth_service import AuthService
from app_server.service.test_member_service import MemberService
from app_server.share import const
from app_server.share.common_util import CommonUtil
from app_server.share.fileIo_util import FileIoUtil
from app_server.share.logger_util import get_logger, log, log_exceptions
from app_server.share.my_exception import UnicornException

# ロガー
logger = get_logger()

router = APIRouter(
    prefix="/tasktag",
    tags=["taskstag"],
    include_in_schema=CommonUtil.is_debug(),  # デバッグモードの場合のみ表示する
)

# 認証URLの指定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/tasktag/login")


class Image(BaseModel):  # noqa: D101
    url: str
    name: str


class User(BaseModel):  # noqa: D101
    name: str = Field(..., min_length=4, max_length=16)  # 4~16文字のstr型
    age: int = Field(..., ge=18, le=99)  # 18~99のint型
    birthday: date  # = Field(..., description="The user's birthday")  # date型

    @field_validator("name")
    @classmethod
    def validate_alphanumeric(cls, v: str) -> str:
        """アルファベットもしくは数字のみで構成された文字列であるかチェックする"""
        if not v.isalnum():
            raise ValueError("must be alphanumeric")
        return v


class Item(BaseModel):  # noqa: D101
    name: str
    description: str | None = None
    price: float
    tax: float | None = None
    tags: set[str] = set()
    image: Image | None = None


@router.get("/tasks/", response_model=dict[str, list[str]])
def list_tasks(response: Response) -> dict[str, list[str]]:
    response.status_code = status.HTTP_400_BAD_REQUEST
    return {"tasks": ["asdf"]}


@router.post("/items2/{item_id}")
def read_item(item_id: str):
    if item_id == "foo":
        return {"id": "foo", "value": "there goes my hero"}
    # UnicornException例外ハンドラーでキャッチできる
    raise UnicornException(name="Item not found")
    # # StarletteHTTPException例外ハンドラーでキャッチできる
    # raise HTTPException(status_code=404, detail="Item not found")


@router.post("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_id": item_id, "item": item}


# 検証
# RequestValidationErrorハンドラーでキャッチしてくれる
# パスオペレーション関数の引数で指定する方法
@router.get("/validate/{item_id}")
async def validate_test(
    item_id: int = Path(title="The ID of the item to get", gt=0, le=1000),
    q: int | None = Query(default=None, alias="item-query"),
):
    results = {"item_id": item_id}
    if q:
        results.update({"q": q})  # type: ignore
    return results


# 検証
# RequestValidationErrorハンドラーでキャッチしてくれる
# モデルで指定する方法
@router.post("/validate2")
async def validate_test2(user: User):
    return user.model_dump()


# Formを使うことでJsonの中のフィールドを直接取得することができる
@router.post("/form/")
async def login(username: str = Form(), password: str = Form()):  # noqa: ARG001
    return {"username": username}


# ファイルアップロード
# こっちのほうがメモリ保存領域を超えた場合にファイルに保存する機能があるので良いらしい
@router.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}


# ファイルアップロード
# ファイルは全てメモリに展開される
@router.post("/files/")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}


# クッキーの取得
@router.get("/cookie/")
async def cookie(ads_id: str | None = Cookie(default=None)):
    return {"ads_id": ads_id}


def query_extractor(q: str | None = None):
    return q


def query_or_cookie_extractor(
    q: Annotated[str, Depends(query_extractor)],
    last_query: str | None = Cookie(default=None),
):
    if not q:
        return last_query
    return q


# Dependsの使用方法
@router.get("/depend/")
async def depend_test(query_or_default: Annotated[str, Depends(query_or_cookie_extractor)]):
    return {"q_or_cookie": query_or_default}


# ログインのエンドポイント
@router.post("/login/")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    # 認証サービスをDI
    auth_service: AuthService = g.injector.resolve(AuthService)
    # JWTトークンで認証処理
    token = auth_service.login(form_data.username, form_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=token)


# フロントエンドはヘッダーに"Bearer <Token>"と付与する必要がある(Swaggerでは自動で付与される)
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """トークンからユーザIDを取得"""
    auth_service: AuthService = g.injector.resolve(AuthService)
    if not auth_service.is_valid_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # トークンではなくユーザモデルを返すことでユーザ情報を参照することができるようになる
    return token


# 認可が必要なエンドポイント
@router.get("/auth/")
async def auth_test(token: Annotated[str, Depends(get_current_user)]):
    return {"token": token}


# DB接続テスト
@router.get("/db/findAll/")
def get_member_list():
    member_service: MemberService = g.injector.resolve(MemberService)
    return member_service.find_all()


@router.get("/db/findById/{id}", summary="IDを指定して検索します", description="idは'1'推奨")
def get_member(member_id: int):
    member_service: MemberService = g.injector.resolve(MemberService)
    return member_service.find_by_id(member_id)


@router.get("/db/update/{id}", summary="IDを指定して名前を更新します", description="idは'1'推奨")
def update_member(member_id: int, member_name: str):
    member_service: MemberService = g.injector.resolve(MemberService)
    member = Member()
    member.member_id = member_id
    member.member_name = member_name
    # 更新後に値が変わるのでコピーしておく
    copied_mamber = copy.deepcopy(member)
    member_service.update(member)
    return copied_mamber


@router.get("/db/getManyToOne/{id}", summary="N:1検索", description="idは'1'推奨")
def get_many_to_one(member_id: int):
    member_repository: MemberRepository = g.injector.resolve(MemberRepository)
    # サービス層を用意していないのでDB設定を明示的に指定
    db: DBConfig = g.injector.resolve(DBConfig)
    return member_repository.find_many_to_one(db, member_id)


@router.get("/db/getOneToMany/{id}", summary="1:N検索", description="idは'1'推奨")
def get_one_to_many(member_id: int):
    member_repository: MemberRepository = g.injector.resolve(MemberRepository)
    # サービス層を用意していないのでDB設定を明示的に指定
    db: DBConfig = g.injector.resolve(DBConfig)
    return member_repository.find_one_to_many(db, member_id)


@router.get("/db/getOneToManyToOne/{id}", summary="1:N:1検索", description="idは'1'推奨")
def get_one_to_many_to_one(member_id: int):
    member_repository: MemberRepository = g.injector.resolve(MemberRepository)
    # サービス層を用意していないのでDB設定を明示的に指定
    db: DBConfig = g.injector.resolve(DBConfig)
    return member_repository.find_one_to_many_to_one(db, member_id)


@router.get("/db/asyncFindAll/", summary="非同期で処理を実行します")
async def async_get_member_list():
    member_service: MemberService = g.injector.resolve(MemberService)
    return await member_service.async_find_all()


# ロガーのテスト
@router.get("/logging/")
@log(logger, "関数の実行状況を出力するデコレーターです")
def get_logger_test():
    # log_exceptionsはログ内容を出力するだけで例外を再スローする
    @log_exceptions(logger)
    def exception_test():
        raise Exception("例外をキャッチするデコレーターです")

    try:
        exception_test()
    except Exception:
        pass
    logger.debug("DEBUGログ")
    logger.info("INFOログ")
    logger.warning("WARNINGログ")
    logger.error("ERRORログ")

    return "TEST"


# 設定ファイル読み込み
@router.get("/setting/")
def get_setting():
    logger.info("設定ファイル読み込み")
    testrow = FileIoUtil.get_properties(const.SETTING_PATH, "TEST", "testrow")
    logger.info(f"[TEST]:testrow`{testrow}`")
    return f"[TEST]:testrow`{testrow}`"
