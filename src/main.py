"""
Main
"""

from threading import Thread

from loguru import logger

from bot.uploading import (
    get_photo_from_attachment,
    get_video_url_noapi,
    download_photo,
    download_video,
    upload_photo,
    upload_video,
    media_id_from_attachment,
)
from bot.bot import Bot, Command, EventContext
from bot.config import DEFAULT_COOKIES_FILE

from executor.delayed import QueueExecutor


vk_bot = Bot()
queue_executor = QueueExecutor()


@vk_bot.command_handler.on_command("help")
def help_command(_: Command, ctx: EventContext) -> None:
    logger.info("Вызвана команда: '/help'")

    def send_help_message():
        try:
            vk_bot.send_message(
                ctx.peer_id,
                """[Помощь]\n\nБот публикует отправленные медиафайлы на стене (клипы и изображения)""",
            )
        except Exception:
            logger.error(
                f"Произошла ошибка в ответе на команду: '/help'. peer_id: {ctx.peer_id}",
            )

    queue_executor.push(send_help_message)


@vk_bot.command_handler.on_attachment("photo")
def photo_attachment(ctx: EventContext) -> None:
    logger.info("Отправлено изображение")

    def publish_photo():
        vk_bot.send_message(ctx.peer_id, "Изображение обрабатывается...")

        url = get_photo_from_attachment(ctx.attachments[0])
        photo = download_photo(url)

        url = upload_photo(vk_bot.user_api, vk_bot.longpoll, photo)

        vk_bot.send_message(
            ctx.peer_id, f"Изображение опубликовано на стене! {url}", ctx.message_id
        )

    queue_executor.push(publish_photo)


@vk_bot.command_handler.on_attachment("video")
def video_attachment(ctx: EventContext) -> None:
    logger.info("Отправлено видео")

    def publish_video():
        vk_bot.send_message(ctx.peer_id, "Видео обрабатывается...")

        video_id = media_id_from_attachment(ctx.attachments[0]["video"])
        video_url = get_video_url_noapi(video_id)
        video = download_video(video_url, cookies_file=DEFAULT_COOKIES_FILE)

        post_url = upload_video(vk_bot.user_api, vk_bot.longpoll, video)

        vk_bot.send_message(
            ctx.peer_id, f"Видео опубликовано на стене! {post_url}", ctx.message_id
        )

    queue_executor.push(publish_video)


if __name__ == "__main__":
    logger.info("Запуск бота...")

    bot_thread = Thread(target=vk_bot.run)
    executor_thread = Thread(target=queue_executor.poll)

    bot_thread.start()
    executor_thread.start()

    logger.info("Бот запущен!")

    bot_thread.join()
    executor_thread.join()
