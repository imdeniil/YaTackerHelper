"""Маршруты для работы с платежами"""

import logging
from datetime import datetime
from fasthtml.common import *
from web.database import get_session, UserCRUD, PaymentRequestCRUD
from web.config import WebConfig
from web.components import (
    page_layout, payment_request_detail, schedule_payment_form, mark_as_paid_form
)
from web.telegram_utils import (
    get_user_profile_photo_url, get_fallback_avatar_url, upload_file_to_storage
)
from bot.database.models import UserRole, PaymentRequestStatus
from .decorators import require_auth, require_role
from .helpers import notify_billing_contacts_about_new_payment

logger = logging.getLogger(__name__)


def setup_payment_routes(app, config: WebConfig):
    """Настраивает маршруты для работы с платежами"""

    @app.post("/payment/create")
    @require_auth
    async def create_payment_request(
        sess,
        request,
        title: str,
        amount: str,
        comment: str,
        invoice_file_id: str = "",
        payment_file_id: str = "",
        created_date: str = "",
        status: str = "pending",
        paid_date: str = "",
        scheduled_date: str = ""
    ):
        """Создание нового запроса на оплату с полной поддержкой всех полей"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        # Проверяем что пользователь существует
        async with get_session() as session:
            user = await UserCRUD.get_user_by_id(session, user_id)
            if not user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'text/html' not in request.headers.get('Accept', ''):
                    return {"success": False, "error": "User not found"}
                return RedirectResponse('/login', status_code=303)

            # Обрабатываем даты
            created_at = None
            if created_date and role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                try:
                    created_at = datetime.strptime(created_date, "%Y-%m-%d")
                except ValueError:
                    pass

            paid_at = None
            if paid_date and status == "paid" and role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                try:
                    paid_at = datetime.strptime(paid_date, "%Y-%m-%d")
                except ValueError:
                    pass

            scheduled_date_obj = None
            if scheduled_date and status == "scheduled" and role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                try:
                    scheduled_date_obj = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Определяем итоговый статус
            final_status = PaymentRequestStatus.PENDING  # По умолчанию для Worker
            if role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                if status == "paid":
                    final_status = PaymentRequestStatus.PAID
                elif status == "scheduled":
                    final_status = PaymentRequestStatus.SCHEDULED_DATE
                else:
                    final_status = PaymentRequestStatus.PENDING

            # Создаем запрос
            payment_request = await PaymentRequestCRUD.create_payment_request(
                session=session,
                created_by_id=user_id,
                title=title,
                amount=amount,
                comment=comment,
                invoice_file_id=invoice_file_id if invoice_file_id else None,
                payment_proof_file_id=payment_file_id if payment_file_id else None,
                status=final_status,
                created_at=created_at,
                paid_at=paid_at,
                paid_by_id=user_id if final_status == PaymentRequestStatus.PAID else None,
                scheduled_date=scheduled_date_obj
            )

            logger.info(f"User {user_id} ({role}) создал запрос на оплату #{payment_request.id} со статусом {final_status.value}")

            # Для Worker отправляем уведомления billing контактам (только для статуса PENDING)
            if role == UserRole.WORKER.value and final_status == PaymentRequestStatus.PENDING:
                await notify_billing_contacts_about_new_payment(
                    session=session,
                    config=config,
                    payment_request=payment_request,
                    user=user,
                    invoice_file_id=invoice_file_id if invoice_file_id else None
                )

        # Для AJAX запросов возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'text/html' not in request.headers.get('Accept', ''):
            return {"success": True, "request_id": payment_request.id}

        # Для обычных форм - редирект
        return RedirectResponse('/dashboard', status_code=303)

    @app.post("/api/upload")
    @require_auth
    async def upload_file(sess, request, file: UploadFile):
        """Загрузка файла в служебный чат Telegram

        Returns:
            JSON с file_id или ошибкой
        """
        user_id = sess.get('user_id')

        # Проверяем что пользователь существует
        async with get_session() as session:
            user = await UserCRUD.get_user_by_id(session, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

        try:
            # Читаем содержимое файла
            file_bytes = await file.read()

            # Проверяем размер файла (максимум 20MB для Telegram)
            if len(file_bytes) > 20 * 1024 * 1024:
                return {"success": False, "error": "File too large (max 20MB)"}

            # Загружаем файл в служебный чат
            file_id = await upload_file_to_storage(
                bot_token=config.bot_token,
                storage_chat_id=config.storage_chat_id,
                file_bytes=file_bytes,
                filename=file.filename or "document"
            )

            if not file_id:
                return {"success": False, "error": "Failed to upload file to Telegram"}

            logger.info(f"User {user_id} uploaded file {file.filename}, file_id: {file_id}")
            return {"success": True, "file_id": file_id, "filename": file.filename}

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/payment/{request_id}")
    @require_auth
    async def payment_detail(sess, request_id: int):
        """Детальная страница запроса на оплату"""
        user_id = sess.get('user_id')
        display_name = sess.get('display_name')
        role = sess.get('role')

        async with get_session() as session:
            current_user = await UserCRUD.get_user_by_id(session, user_id)
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может видеть только свои запросы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

        content = payment_request_detail(payment_request, role)

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(config.bot_token, current_user.telegram_id) if current_user else None
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(display_name)

        return page_layout(
            f"Запрос на оплату #{request_id}",
            content,
            display_name,
            role,
            avatar_url
        )

    @app.post("/payment/{request_id}/schedule")
    @require_auth
    @require_role(UserRole.OWNER.value, UserRole.MANAGER.value)
    async def schedule_payment(sess, request_id: int, schedule_type: str, scheduled_date: str = None):
        """Планирование оплаты"""
        user_id = sess.get('user_id')

        async with get_session() as session:
            if schedule_type == "today":
                await PaymentRequestCRUD.schedule_payment(
                    session=session,
                    request_id=request_id,
                    processing_by_id=user_id,
                    is_today=True
                )
            else:
                # Парсим дату из строки формата YYYY-MM-DD
                scheduled_date_obj = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
                await PaymentRequestCRUD.schedule_payment(
                    session=session,
                    request_id=request_id,
                    processing_by_id=user_id,
                    scheduled_date=scheduled_date_obj
                )

            logger.info(f"User {user_id} запланировал оплату запроса #{request_id}")

        return RedirectResponse(f'/payment/{request_id}', status_code=303)

    @app.post("/payment/{request_id}/pay")
    @require_auth
    @require_role(UserRole.OWNER.value, UserRole.MANAGER.value)
    async def mark_payment_as_paid(sess, request_id: int):
        """Отметка запроса как оплаченного (без загрузки файла)"""
        user_id = sess.get('user_id')

        async with get_session() as session:
            # Временно используем пустой file_id, т.к. загрузка файла будет через бот
            await PaymentRequestCRUD.mark_as_paid(
                session=session,
                request_id=request_id,
                paid_by_id=user_id,
                payment_proof_file_id="web_payment",  # Временная заглушка
                processing_by_id=user_id
            )

            logger.info(f"User {user_id} отметил запрос #{request_id} как оплаченный")

        return RedirectResponse(f'/payment/{request_id}', status_code=303)

    @app.post("/payment/{request_id}/cancel")
    @require_auth
    async def cancel_payment(sess, request_id: int):
        """Отмена запроса на оплату"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может отменять только свои запросы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

            await PaymentRequestCRUD.cancel_payment_request(session, request_id)
            logger.info(f"User {user_id} отменил запрос #{request_id}")

        return RedirectResponse('/dashboard', status_code=303)

    @app.get("/payment/{request_id}/download/invoice")
    @require_auth
    async def download_invoice(sess, request_id: int):
        """Скачивание счета"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может скачивать только свои файлы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

            if not payment_request.invoice_file_id:
                return RedirectResponse(f'/payment/{request_id}', status_code=303)

            # Получаем URL файла из Telegram
            import httpx
            async with httpx.AsyncClient() as client:
                # Получаем информацию о файле
                file_response = await client.get(
                    f"https://api.telegram.org/bot{config.bot_token}/getFile",
                    params={"file_id": payment_request.invoice_file_id}
                )

                if file_response.status_code != 200:
                    logger.error(f"Не удалось получить файл счета для запроса #{request_id}")
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_data = file_response.json()
                if not file_data.get("ok"):
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_path = file_data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{config.bot_token}/{file_path}"

                # Редирект на файл
                return RedirectResponse(file_url, status_code=303)

    @app.get("/payment/{request_id}/download/proof")
    @require_auth
    async def download_payment_proof(sess, request_id: int):
        """Скачивание платежки"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может скачивать только свои файлы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

            if not payment_request.payment_proof_file_id:
                return RedirectResponse(f'/payment/{request_id}', status_code=303)

            # Получаем URL файла из Telegram
            import httpx
            async with httpx.AsyncClient() as client:
                # Получаем информацию о файле
                file_response = await client.get(
                    f"https://api.telegram.org/bot{config.bot_token}/getFile",
                    params={"file_id": payment_request.payment_proof_file_id}
                )

                if file_response.status_code != 200:
                    logger.error(f"Не удалось получить файл платежки для запроса #{request_id}")
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_data = file_response.json()
                if not file_data.get("ok"):
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_path = file_data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{config.bot_token}/{file_path}"

                # Редирект на файл
                return RedirectResponse(file_url, status_code=303)
