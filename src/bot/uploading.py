"""
Загрузка и выгрузка видео и изображений по URL из VK
"""

import os
import time
import tempfile
from io import BytesIO
from typing import Dict, Any

import requests
import yt_dlp

from loguru import logger

from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.upload import VkUpload


def download_video(video_url: str, cookies_file: str | None = None) -> BytesIO:
    """Загружает видео в BytesIO буффер по URL через yt-dlp"""
    buffer = BytesIO()

    ydl_opts = {
        "Quiet": True,
        "cookiefile": cookies_file,
        "outtmpl": os.path.join(tempfile.gettempdir(), "%(id)s.%(ext)s"),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filepath = ydl.prepare_filename(info)

        with open(filepath, "rb") as f:
            buffer.write(f.read())

    return buffer


def download_photo(photo_url: str) -> BytesIO:
    """Загружает изображение в BytesIO буффер по URL"""
    photo_response = requests.get(photo_url)

    if photo_response.status_code != 200:
        raise ValueError(f"Не удалось загрузить изображение по url: {photo_url}")

    return BytesIO(photo_response.content)


def get_video_url_api(vk_user_api: VkApi, video_id: str) -> str:
    """Позвращает URL видеоплеера по ID видео. Требует VK User Session"""
    video_response = vk_user_api.method(
        "video.get",
        values={"videos": video_id},
    )

    video_items = video_response["items"]
    if len(video_items) == 0:
        raise ValueError(f"Видео с ID: {video_id} не найдено!")

    video = video_items[0]
    if "player" not in video.keys():
        raise ValueError(f"Плеер в видео с ID: {video_id} не найден!")

    return video["player"]


def get_video_url_noapi(video_id: str) -> str:
    """Альтернативный способ получить URL видео по ID"""
    parts = video_id.split("_")

    first = f"video{parts[0]}"
    second = f"_{parts[1]}"
    third = f"_{parts[2]}" if len(parts) == 3 else ""

    return f"https://vk.com/{''.join([first, second, third])}"


def get_photo_from_attachment(attachment: Dict[str, Any]) -> str:
    """Возвращает изображение максимального разрешения из VK Message Attachment"""
    if "type" not in attachment.keys() or attachment["type"] != "photo":
        raise ValueError("Прикрепленный медиаконтент не является изображением!")

    photo = list(
        filter(lambda size: size["type"] == "base", attachment["photo"]["sizes"])
    )[0]

    return photo["url"]


def media_id_from_attachment(attachment: Dict[str, Any]) -> str:
    """Возвращает Media ID из VK Message Attachment"""
    id_ = attachment["id"]
    owner_id = attachment["owner_id"]
    access_key = attachment["access_key"] if "access_key" in attachment.keys() else None

    if access_key:
        return f"{owner_id}_{id_}_{access_key}"
    else:
        return f"{owner_id}_{id_}"


def upload_clip(
    vk_user_api: VkApi,
    vk_group_bot: VkBotLongPoll,
    video: BytesIO,
    upload_wait_time: int = 10,
) -> str:
    """
    Публикует клип на стену группы ВК
    Требует VK User Session для загрузки на Media Server и VK Bot Session для публикации на стене группы
    """
    video_size = video.getbuffer().nbytes
    api = vk_user_api.get_api()

    clip_uploader = api.shortVideo.create(
        group_id=vk_group_bot.group_id, file_size=video_size
    )

    logger.info("Загрузка клипа на upload сервер...")
    uploader_response = vk_user_api.http.post(
        clip_uploader["upload_url"], files={"file": video.getvalue()}
    )
    uploaded_clip = uploader_response.json()

    time.sleep(upload_wait_time)

    logger.info("Редактирование клипа...")
    api.shortVideo.edit(
        video_id=uploaded_clip["video_id"],
        owner_id=uploaded_clip["owner_id"],
        privacy_view="all",
        can_make_duet=0,
    )

    time.sleep(10)

    logger.info("Публикация клипа...")
    published_clip = api.shortVideo.publish(
        video_id=uploaded_clip["video_id"],
        owner_id=uploaded_clip["owner_id"],
        license_agree=1,
        publish_date=0,
        wallpost=1,
    )

    wall_post_id = None
    if "video" in published_clip and "wall_post_id" in published_clip["video"]:
        wall_post_id = published_clip["video"]["wall_post_id"]
    elif "wall_post_id" in published_clip:
        wall_post_id = published_clip["wall_post_id"]

    published_clip_url = f"https://vk.com/wall-{vk_group_bot.group_id}_{wall_post_id}"

    logger.success(f"Опубликован клип: {published_clip_url}")

    return published_clip_url


def upload_video(
    vk_user_api: VkApi,
    vk_group_bot: VkBotLongPoll,
    video: BytesIO,
) -> str:
    """
    Публикует видео на стену группы ВК
    Требует VK User Session для загрузки на Media Server и VK Bot Session для публикации на стене группы
    """
    api = vk_user_api.get_api()

    logger.info("Загрузка видео на upload сервер...")

    uploader_response = api.video.save(
        group_id=vk_group_bot.group_id,
        repeat=True,
    )

    uploaded_video = vk_user_api.http.post(
        uploader_response["upload_url"],
        files={"video_file": video.getvalue()},
    ).json()

    attachment = f"video{uploaded_video['owner_id']}_{uploaded_video['video_id']}"
    posted_video = api.wall.post(
        owner_id=f"-{vk_group_bot.group_id}",
        from_group=1,
        close_comments=1,
        attachments=attachment,
    )

    posted_video_url = (
        f"https://vk.com/wall-{vk_group_bot.group_id}_{posted_video['post_id']}"
    )

    logger.success(f"Опубликовано видео: {posted_video_url}")

    return posted_video_url


def upload_photo(
    vk_user_api: VkApi, vk_group_bot: VkBotLongPoll, photo: BytesIO
) -> str:
    """
    Публикует изображение на стену группы ВК
    Требует VK User Session для загрузки на Media Server и VK Bot Session для публикации на стене группы
    """
    upload = VkUpload(vk_user_api)
    api = vk_group_bot.vk.get_api()

    logger.info("Загрузка изображения на upload сервер...")
    uploader_response = upload.photo_wall(
        group_id=vk_group_bot.group_id, photos=[photo]
    )[0]

    attachment = f"photo{uploader_response['owner_id']}_{uploader_response['id']}"

    logger.info("Публикация изображения...")
    posted_photo = api.wall.post(
        owner_id=f"-{vk_group_bot.group_id}",
        from_group=1,
        close_comments=1,
        attachments=attachment,
    )

    posted_photo_url = (
        f"https://vk.com/wall-{vk_group_bot.group_id}_{posted_photo['post_id']}"
    )

    logger.success(f"Опубликовано изображение: {posted_photo_url}")

    return posted_photo_url
