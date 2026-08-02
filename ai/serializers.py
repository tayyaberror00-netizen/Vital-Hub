from rest_framework import serializers


class NutritionInputSerializer(serializers.Serializer):
    age      = serializers.IntegerField(min_value=1, max_value=120)
    weight   = serializers.FloatField(min_value=20.0, max_value=500.0)
    height   = serializers.FloatField(min_value=50.0,  max_value=300.0)
    goal     = serializers.ChoiceField(choices=['loss', 'gain', 'perf', 'focus', 'maintain'])
    gender   = serializers.ChoiceField(choices=['male', 'female'], default='male',     required=False)
    activity = serializers.ChoiceField(
        choices=['sedentary', 'light', 'moderate', 'active', 'very_active'],
        default='moderate',
        required=False,
    )


class ConsultationChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    history = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class NutritionPlanSerializer(serializers.Serializer):
    weight     = serializers.FloatField(min_value=20.0, max_value=500.0)
    height     = serializers.FloatField(min_value=50.0, max_value=300.0)
    age        = serializers.IntegerField(min_value=1, max_value=120)
    gender     = serializers.ChoiceField(choices=['male', 'female'])
    goal       = serializers.CharField(max_length=50)
    activity   = serializers.CharField(max_length=50)
    calories   = serializers.IntegerField()
    diseases   = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    halal      = serializers.BooleanField(required=False, default=False)
    budget     = serializers.BooleanField(required=False, default=False)
    exclusions = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    location   = serializers.CharField(required=False, default='Pakistan', allow_blank=True)
    report_context = serializers.CharField(required=False, allow_blank=True, default='')


class GroceryListSerializer(serializers.Serializer):
    week_plan = serializers.ListField(child=serializers.DictField())
    budget    = serializers.BooleanField(required=False, default=False)
