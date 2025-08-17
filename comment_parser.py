import asyncio
from datetime import datetime
import re

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CommentParser:

    def __init__(self):
        self.browser: Browser = None
        self.page: Page = None
        self.context: BrowserContext = None

    async def init_browser(self):
        """Инициализация браузера Playwright"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                channel='chrome',
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            logger.info("🌐 Браузер Playwright инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации браузера: {e}")
            raise

    async def parse_search_page(self, product_url: str):
        """Парсинг страницы товара DNS"""
        try:
            logger.info(f"🌐 Открываю страницу товара: {product_url}")

            # Случайная задержка перед загрузкой (1-3 секунды)
            delay = asyncio.sleep(1 + (hash(product_url) % 3))
            await delay

            # Пробуем загрузить страницу с повторными попытками
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🌐 Попытка {attempt + 1}/{max_retries} загрузки страницы")
                    await self.page.goto(product_url, wait_until='networkidle', timeout=30000)
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)  # Ждем перед повторной попыткой
                    else:
                        logger.error(f"❌ Не удалось загрузить страницу после {max_retries} попыток")
                        return None

            # Ждем загрузки страницы товара
            await asyncio.sleep(3)

            # Случайная пауза для имитации человеческого поведения
            await asyncio.sleep(1 + (hash(product_url) % 2))

            # Проверяем, что страница загрузилась успешно
            page_title = await self.page.title()
            if "403" in page_title or "Forbidden" in page_title:
                logger.error("❌ Получена ошибка 403 - доступ запрещен")
                return None

            # Парсим данные продукта
            product_data = []

            try:
                counter = 0
                while True:
                    counter += 1
                    logger.info(f"Загрузка комментариев №{counter}")
                    is_hidden = await self.page.locator('.opinions-widget__pagination').is_hidden()
                    if is_hidden:
                        logger.info("Подгружены все комментарии")
                        break
                    show_more_button = self.page.locator('button.button-ui_grey:has-text("Показать ещё")')
                    await show_more_button.click()
                    await self.page.wait_for_timeout(5000)
                load_opinions = await self.page.locator(".ui-link_blue.ui-link_pseudolink.ui-collapse__link").all()
                for opinion in load_opinions:
                    await opinion.click()
                load_more_opinions = await self.page.locator(".ui-link_pseudolink[data-role='open-answers']").all()
                answer_counter = 0
                for i in load_more_opinions:
                    answer_counter += 1
                    print(f'Загрузка ответов комментариев {answer_counter}')
                    await i.click()
                print("Загрузка ответов комментариев завершена")

                reviews_data = []
                comments_data = []
                media_data = []

                # Основной блок комментариев
                reviews_blocks = await self.page.query_selector_all('.ow-opinion.ow-opinions__item')

                for block in reviews_blocks:
                    if block:
                        reviews_dict = {}

                        # Достоинства
                        plus = await block.query_selector('.ow-opinion__text:has-text("Достоинства")')
                        if plus:
                            plus_text = await plus.text_content()
                            reviews_dict['plus'] = plus_text[11:]
                        else:
                            reviews_dict['plus'] = None

                        # Недостатки
                        minus = await block.query_selector('.ow-opinion__text:has-text("Недостатки")')
                        if minus:
                            minus_text = await minus.text_content()
                            reviews_dict['minus'] = minus_text[10:]
                        else:
                            reviews_dict['minus'] = None

                        # Комментарий
                        review = await block.query_selector('.ow-opinion__text:has-text("Комментарий")')
                        if review:
                            review_text = await review.text_content()
                            reviews_dict['review'] = review_text[11:]
                        else:
                            reviews_dict['review'] = None

                        # Рейтинг
                        rating = await block.query_selector_all(".star-rating__star[data-state='selected']")
                        reviews_dict['rating'] = len(rating) / 2

                        # Реальный покупатель
                        user_id_real = await block.query_selector('.profile-info__real')
                        if user_id_real:
                            reviews_dict['user_id_real'] = True
                        else:
                            reviews_dict['user_id_real'] = False

                        # Дата отзыва
                        date = await block.query_selector('.ow-opinion__date')
                        if date:
                            date_text = await date.text_content()
                            reviews_dict['date'] = datetime.strptime(date_text, "%d.%m.%Y")

                        # UUID Отзыва
                        opinion_id = await block.get_attribute('data-opinion-id')
                        if opinion_id:
                            reviews_dict['id'] = opinion_id

                        # UUID Пользователя
                        user_id = await block.get_attribute('data-user-id')
                        if user_id:
                            reviews_dict['user_id'] = user_id

                        is_top = await block.query_selector('.ow-opinion__most-popular')
                        if is_top:
                            reviews_dict['is_top'] = True
                        else:
                            reviews_dict['is_top'] = False

                        reviews_data.append(reviews_dict)

                        comments = await block.query_selector_all('.comment')
                        for comment in comments:
                            if comment:
                                comments_dict = {}
                                comment_id = await comment.get_attribute('data-id')
                                if comment_id:
                                    comments_dict['comment_id'] = comment_id
                                comments_dict['review_id'] = opinion_id
                                user_id = await comment.query_selector('.profile-info__name')
                                if user_id:
                                    user_id = await user_id.get_attribute('data-user-popover-url')
                                if user_id:
                                    match = re.search(r'userId=([a-f0-9-]+)', user_id)
                                    if match:
                                        user_id = match.group(1)
                                    else:
                                        raise Exception('Не совпал user_id по регулярному выражению')

                                comments_dict['user_id'] = user_id
                                if user_id == '0ebcb82d-1907-4359-b365-ddd7af5fe906':
                                    comments_dict['is_admin'] = True
                                else:
                                    comments_dict['is_admin'] = False
                                text = await comment.query_selector('.comment__message.message')
                                if text:
                                    text = await text.text_content()
                                    comments_dict['text'] = text.strip()
                                date = await comment.query_selector('.comment__date.time-info')
                                if date:
                                    date = await date.text_content()
                                    comments_dict['date'] = date.strip()
                                comments_data.append(comments_dict)

                        media_objects = await block.query_selector('.ow-photos-and-videos')
                        if media_objects:
                            img_elements = await media_objects.query_selector_all('img')
                            video_elements = await media_objects.query_selector_all('video')
                            if img_elements:
                                for img in img_elements:
                                    media_dict = {}
                                    url = await img.get_attribute('src')
                                    if url:
                                        media_dict['media_url'] = url
                                        media_dict['review_id'] = opinion_id
                                        media_data.append(media_dict)
                            if video_elements:
                                for video in video_elements:
                                    media_dict = {}
                                    url = await video.get_attribute('src')
                                    if url:
                                        media_dict['media_url'] = url
                                        media_dict['review_id'] = opinion_id
                                        media_data.append(media_dict)



                # print(reviews_data)
                # print(comments_data)
                print(media_data)

                await asyncio.Future()
            except Exception as e:
                logger.warning(f"⚠️ Не удалось спарсить данные товара: {e}")
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга страницы товара {product_url}: {e}")
            return None

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("🧹 Ресурсы очищены")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки: {e}")

    async def run(self):
        """Основной метод запуска парсера"""
        try:
            logger.info("🚀 Запуск парсера продуктов")

            # Инициализация
            await self.init_browser()

            # Обработка
            await self.parse_search_page(
                'https://www.dns-shop.ru/product/opinion/eaa728bcf803d582/termopasta-id-cooling-frost-x45/')


        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            await self.cleanup()


async def main():
    parser = CommentParser()
    await parser.run()


if __name__ == '__main__':
    asyncio.run(main())
