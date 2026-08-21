from austial import Injectable

from src.i18n.i18n import t


@Injectable()
class AppService:
    def get_hello(self) -> dict:
        return {"message": t("app.hello_message")}
