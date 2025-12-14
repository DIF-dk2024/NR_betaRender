from flask import Flask, send_from_directory, request, jsonify
import os
import base64
import datetime
import requests  # важно: есть в requirements.txt

# Статические файлы (index.html, analyzer.html, sample.csv) лежат в корне
app = Flask(__name__, static_folder=".", static_url_path="")


# ---------- вспомогательная функция для GitHub ----------

def github_update_csv(line: str):
    """
    Добавляет строку line в CSV-файл в приватном репозитории на GitHub.
    Репозиторий и файл задаются переменными окружения:
    - GITHUB_REPO  (например 'DIF-dk2024/NR_betaRender_orders')
    - GITHUB_FILE  (например 'orders.csv')
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")      # 'DIF-dk2024/NR_betaRender_orders'
    path = os.environ.get("GITHUB_FILE", "orders.csv")

    if not token or not repo:
        raise RuntimeError("GITHUB_TOKEN или GITHUB_REPO не заданы в переменных окружения")

    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    # 1) Получаем текущий файл, если он есть
    resp = requests.get(api_url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        sha = data["sha"]
        content_b64 = data["content"]
        existing = base64.b64decode(content_b64).decode("utf-8")
        if not existing.endswith("\n"):
            existing += "\n"
        new_content = existing + line
    elif resp.status_code == 404:
        # файла нет — создаём новый с заголовком
        header = "timestamp;budget_min;budget_max;floor;rooms;analysis_type;contact;comment\n"
        new_content = header + line
        sha = None
    else:
        raise RuntimeError(f"GitHub GET failed: {resp.status_code} {resp.text}")

    payload = {
        "message": "add order from landing",
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=payload)
    if put_resp.status_code not in (200, 201):
        raise RuntimeError(f"GitHub PUT failed: {put_resp.status_code} {put_resp.text}")


# ---------- фронтовые маршруты ----------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/analyzer.html")
def analyzer():
    return send_from_directory(".", "analyzer.html")


@app.route("/sample.csv")
def sample():
    return send_from_directory(".", "sample.csv")


# ---------- API для формы заказа анализа ----------

@app.route("/api/order", methods=["POST"])
def api_order():
    try:
        data = request.get_json(force=True, silent=False) or {}
    except Exception:
        return jsonify(ok=False, error="invalid JSON"), 400

    # Забираем поля из JSON
    budget_min = (data.get("budget_min") or "").strip()
    budget_max = (data.get("budget_max") or "").strip()
    floor      = (data.get("floor") or "").strip()
    rooms      = (data.get("rooms") or "").strip()
    analysis_type = (data.get("analysis_type") or "").strip()
    contact    = (data.get("contact") or "").strip()
    comment    = (data.get("comment") or "").strip()

    if not contact:
        return jsonify(ok=False, error="нужны контакты, чтобы я мог ответить"), 400

    ts = datetime.datetime.utcnow().isoformat()

    def clean(val: str) -> str:
        """чтоб не ломать CSV: заменяем ; и переносы строк"""
        return val.replace(";", ",").replace("\n", " ").replace("\r", " ")

    line = ";".join([
        clean(ts),
        clean(budget_min),
        clean(budget_max),
        clean(floor),
        clean(rooms),
        clean(analysis_type),
        clean(contact),
        clean(comment),
    ]) + "\n"

    try:
        github_update_csv(line)
    except Exception as e:
        print("ERROR github_update_csv:", e, flush=True)
        return jsonify(ok=False, error="не удалось сохранить заявку"), 500

    return jsonify(ok=True)


# ---------- локальный запуск (не для Render) ----------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


@app.route("/trend")
def trend():
    # Страница с графиком (Plotly CDN)
    return send_from_directory(".", "astana_dec_plotly_cdn_v3.html")


# Короткий алиас (опционально)
@app.route("/astana/dec")
def astana_dec_trend():
    return send_from_directory(".", "astana_dec_plotly_cdn_v3.html")

