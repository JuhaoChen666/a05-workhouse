import os

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks



inference_pipeline = pipeline(
    task=Tasks.emotion_recognition,
    model="iic/emotion2vec_plus_large")

rec_result = inference_pipeline(
    "D:/a05-workhouse/FastAPI-Backend/data/audio/20260224/frontend_test_user_20260224_022305.wav",
    granularity="utterance",

)
print(rec_result)