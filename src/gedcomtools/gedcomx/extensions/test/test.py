from gedcomtools.gedcomx.schemas import extensible

@extensible()
class TestClass:
    def __init__(self,arg1: str,arg2: str) -> None:
        arg1 = arg1
        self.arg2 = arg2

