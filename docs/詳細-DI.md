# 詳細-DI

**※pythonライブラリ[Injector](https://github.com/python-injector/injector)についての説明です。**

**※Fast APIのdependenciesの説明ではありません。**

# Injectorライブラリの使い方

## インストール

下記コマンドでインストール

```
$ pip install injector==0.21.0

```

## 基本的なDI

### **ディレクトリ構造**

```
│  ex_service.py
│  di.py
│  main.py

```

### 実装

```python
# ex_service.py

# 抽象クラス
class Car(metaclass=ABCMeta):
    @abstractmethod
    def disp_car_type(self) -> None:
        raise NotImplementedError

# 抽象クラス
class Color(metaclass=ABCMeta):
    @abstractmethod
    def disp_color(self) -> None:
        raise NotImplementedError

# 抽象クラスを実装した具象クラス
class SuperCar(Car):
    @inject
    def __init__(self, color: Color):  # ColorのインスタンスをDI
        self.color = color
        print("car初期化")

    def disp_car_type(self):
        # 色も表示する
        self.color.disp_color()
        print("car type is super car")

# シングルトンスコープで実装
@singleton
class Yellow(Color):
    def __init__(self):
        print("yellow初期化")

    def disp_color(self):
        print("color is yellow")

@inject
@dataclass
class ExService:
    car: Car

    def action(self) -> None:
        self.car.disp_car_type()

```

- インジェクトするクラスやメソッドに@injectをつけるだけでよい
- プロトタイプスコープ以外のスコープを使用する場合、例えばシングルトンスコープの場合はクラスに@singletonをつける。

```python
# di.py

class DI:
    """Dependency Injectionを実現する"""

    def __init__(self) -> None:
        # 依存関係を設定する関数を読み込む
        self.injector = Injector(self.__class__.config)

    # 依存関係を設定するメソッド
    @classmethod
    def config(cls: type, binder: Binder):
        # バインド
        binder.bind(interface=Car, to=SuperCar)
        binder.bind(interface=Color, to=Yellow)

    # injector.get()に引数を渡すと依存関係を解決してインスタンスを生成する
    def resolve(self, cls: type):
        return self.injector.get(cls, scope_id=scope_id)

```

configのところは「[【Python】injectorでDIコンテナを実装する](https://qiita.com/Jazuma/items/9fa15b36f61f9d1e770c)」を参考にしています。

[公式ドキュメント](https://github.com/python-injector/injector/blob/master/docs/practices.rst#injecting-into-constructors-vs-injecting-into-other-methods)だとmoduleインターフェースを継承したクラスを作成するようですが、configを使用したほうがわかりやすいので採用する。

```python
# main.py

def main():
    # Dependency クラスをインスタンス化
    injector = DI()

    # インスタンスを生成
    a1: ExService = injector.resolve(ExService)
    a2: ExService = injector.resolve(ExService)
    a1.action()
    a2.action()

if __name__ == "__main__":
    # ログを表示したい場合は下記2行をコメントアウト
    # logging.basicConfig(level=logging.DEBUG)
    # logging.getLogger("injector").setLevel(logging.DEBUG)
    main()]

```

### 実行結果

```
yellow初期化
car初期化
car初期化
color is yellow
car type is super car
color is yellow
car type is super car
```

車→スーパーカー、色→黄色 の実装ができています。