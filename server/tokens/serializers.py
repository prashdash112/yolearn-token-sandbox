from rest_framework import serializers

class QuoteReq(serializers.Serializer):
    tool = serializers.ChoiceField(choices=["chat", "flashcards", "ppt", "short_video", "live_audio_chat"])
    params = serializers.DictField(child=serializers.JSONField(), required=False)

class UsageReq(serializers.Serializer):
    quote_id = serializers.CharField()
    llm_in_1k = serializers.FloatField(required=False, default=0)
    llm_out_1k = serializers.FloatField(required=False, default=0)
    stt_min = serializers.FloatField(required=False, default=0)
    tts_min = serializers.FloatField(required=False, default=0)
    video_min = serializers.FloatField(required=False, default=0)
    images_1024 = serializers.IntegerField(required=False, default=0)
    images_2048 = serializers.IntegerField(required=False, default=0)
    gpu_seconds = serializers.IntegerField(required=False, default=0)
    meta = serializers.JSONField(required=False)