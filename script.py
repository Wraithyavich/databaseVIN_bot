import asyncio
from fastapi import FastAPI, Query, HTTPException
from playwright.async_api import async_playwright
import uvicorn
import re

app = FastAPI()

async def parse_exist(vin: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # Переходим на страницу поиска Exist
            await page.goto(f"https://www.exist.ru/price/?q={vin}")
            # Ждём загрузки результатов (можно ориентироваться на конкретный селектор)
            await page.wait_for_selector(".result-table", timeout=10000)
            # Извлекаем артикулы турбин (предположим, они содержат "Turbo" или имеют класс)
            # Это очень упрощённый пример; реальный парсинг зависит от структуры сайта
            content = await page.content()
            # Используем регулярное выражение для поиска артикулов (пример)
            turbo_articles = re.findall(r'[A-Z0-9]{5,20}', content)
            # Фильтруем только те, что похожи на артикулы турбин (например, содержат "TURBO")
            turbo_articles = [a for a in turbo_articles if "TURBO" in a.upper()]
            return list(set(turbo_articles))  # уникальные
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            await browser.close()

@app.get("/search")
async def search_vin(vin: str = Query(..., min_length=10)):
    articles = await parse_exist(vin)
    return {"vin": vin, "articles": articles}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
