# Ets Garba — website and WhatsApp assistant

The FastAPI application serves the Ets Garba website and a WhatsApp chatbot (Meta Cloud API) backed by Claude. The website is a lightweight, bilingual static frontend in `web/`; the webhook provides per-user conversation memory, signature verification, and duplicate-delivery protection.

## Website deployment
The website deploys from this repository to its GitHub Pages project URL when changes are pushed to the default branch. The deployment workflow publishes the static files in `web/`; the FastAPI app and WhatsApp webhook remain available when the Python application is hosted separately.

## Setup
1. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   uvicorn app.main:get_app --factory --port 8000
   ```
3. Visit `http://localhost:8000`. The website is served from the same app as the WhatsApp webhook.

## WhatsApp setup
1. Create a Meta app with the WhatsApp product; note the **access token**, **phone number ID**, and **app secret**.
2. Copy `.env.example` to `.env` and fill in the values (plus `ANTHROPIC_API_KEY`).
3. Expose the app (e.g. `ngrok http 8000`) and set the webhook in Meta to `https://<host>/webhook` with your `WHATSAPP_VERIFY_TOKEN`; subscribe to the `messages` field.

The website's quote form prepares an email to `contact@etsgarba.com`; it does not submit personal information to the server. Phone, WhatsApp, street address, and opening hours are intentionally omitted until verified details are available.

The Central African Republic silhouette in `web/static/car-flag-map.svg` is based on Natural Earth's public-domain 1:110m country boundaries. The flag colours and star are used as a visual treatment, not as an official cartographic rendering.

## Brand assets
The header and footer use the standalone geometric Garba “G” monogram; the CAR map and flag artwork is used only as a national-pride visual, not as the company logo. The site self-hosts Fraunces and Manrope under the SIL Open Font License 1.1; the license texts are in `web/static/fonts/`.

Service photography is stored locally in `web/static/images/` and used under the Unsplash License (free commercial use; attribution is appreciated). Each is labelled as an illustrative stock photo; none depicts Ets Garba’s actual projects, staff, inventory, vehicles, or partners. Source images: [general trade — market textiles and clothing by Jonathan Lim](https://unsplash.com/photos/colorful-textiles-and-clothing-displayed-in-a-market-DyQhY4HxP9k), [import-export — cargo ship by Kinsey Wang](https://images.unsplash.com/photo-1722413890462-1bffb6fe082b), [automotive — mechanic by Joseph Pillado](https://images.unsplash.com/photo-1711386689622-1cda23e10217), [vehicle hire — van by Bjarne Vijfvinkel](https://images.unsplash.com/photo-1623094701717-b186ec95acff), [equipment — technician by Valentin Lacoste](https://images.unsplash.com/photo-1785682117029-86171f64c826), [contracts — document review by Mugabi Owen](https://images.unsplash.com/photo-1767871495063-82d150582a23), and [international representation — business colleagues by Vitaly Gariev](https://images.unsplash.com/photo-1758518727343-e578b7795ad5).

## Behaviour
- Text messages go to Claude; replies are sent back, split if over WhatsApp's 4096-char limit.
- Send `/reset` to clear a conversation.
- Non-text messages get a short "text only" notice.
- `ALLOWED_NUMBERS` restricts who can use the bot (recommended while testing).

## Tests
```bash
python -m pytest
```

## Notes
- History is in-memory and lost on restart; use Redis/a DB for multi-instance deployments.
- The system prompt is configurable via `SYSTEM_PROMPT`.
