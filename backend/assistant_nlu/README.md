# NoobTrade Assistant NLU

This folder is the training workspace for the NoobTrade voice assistant.

The production assistant now has three layers:

1. Product action registry in the Vue app.
2. Cloud intent router at `/api/assistant/intent`.
3. Rasa-compatible training data in this folder, fed by real user corrections from `/api/assistant/feedback`.

Rasa is best used here as our own command-understanding model: intent classification plus entity extraction for pages, indicators, symbols, probability thresholds, starred watchlist actions, Generate/Search, and historical-pattern controls.

It is not meant to replace the cloud reasoning layer. The long-term design is:

- Rasa handles known NoobTrade UI commands fast and consistently.
- The cloud reasoning layer handles ambiguous phrasing and natural conversation.
- User corrections are stored in Postgres, exported into Rasa training examples, reviewed, and used to retrain.

When a trained Rasa service is deployed, point the Flask backend at it:

```bash
ASSISTANT_INTENT_PROVIDER=rasa
ASSISTANT_RASA_URL=https://your-rasa-service.example.com
```

The backend calls `POST /model/parse`, converts Rasa entities into NoobTrade UI actions, and still falls back to OpenAI/rules if the Rasa service is unavailable.

## Iteration Loop

1. Users speak naturally in NoobTrade.
2. If the assistant gets it wrong, the user can say: `wrong, I meant select RSI` or `不是，我是说打开股票分析`.
3. The frontend sends the prior prediction plus correction to `/api/assistant/feedback`.
4. Feedback is stored in the `assistant_intent_feedback` table.
5. Export examples:

```bash
cd backend
PYTHONPATH=. ./.venv/bin/python scripts/export_assistant_feedback.py
```

6. Review `assistant_nlu/data/generated_feedback.yml`.
7. Retrain Rasa outside the Render web service:

```bash
rasa train --domain assistant_nlu/domain.yml --config assistant_nlu/config.yml --data assistant_nlu/data
```

## Why Not Ship Rasa Inside Render Yet?

Rasa is heavier than the current Flask service. We should train it as a separate worker/service later, then call it from `/api/assistant/intent`. Keeping training outside the main web service avoids slow deploys and memory spikes.
