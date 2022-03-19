import uvicorn
from fastapi import FastAPI
from transformers import BartForConditionalGeneration, BartTokenizer

from gibbs import Hub, Worker


PORT = 8000
N_WORKERS = 2


# Create our worker, which is just a BART model, that we will use for
# text summarization
class BartSummarizer:
    def __init__(self, model="facebook/bart-large-cnn"):
        super().__init__()

        self.tokenizer = BartTokenizer.from_pretrained(model)
        self.model = BartForConditionalGeneration.from_pretrained(model)

    def __call__(self, text):
        inputs = self.tokenizer([text], max_length=1024, truncation=True, return_tensors="pt")
        summary_ids = self.model.generate(inputs["input_ids"], num_beams=4, max_length=36)
        summary = self.tokenizer.batch_decode(
            summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return summary


# Instanciate the hub, create the FastAPI app, declare a route
app = FastAPI()
hub = Hub()


@app.get("/summarize")
async def simple_request(article: str):
    return {"article": article, "summary": await hub.request(text=article)}


def main():
    # Start our workers
    for _ in range(N_WORKERS):
        w = Worker(BartSummarizer, model="sshleifer/distilbart-cnn-6-6")
        w.start()

    # Serve the API
    uvicorn.run(app, host="0.0.0.0", port=PORT)

    # You can just access `http://localhost:8000/docs` and try the `summarize` route !


if __name__ == "__main__":
    main()
