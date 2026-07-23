from rest_framework import serializers


class HealthCheckDataSerializer(serializers.Serializer):
    status = serializers.CharField()
    checks = serializers.DictField(child=serializers.CharField())


class HealthCheckSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = HealthCheckDataSerializer()


class HealthCheckErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    errors = HealthCheckDataSerializer()
