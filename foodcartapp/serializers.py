from django.db import transaction
from rest_framework.serializers import ModelSerializer
from phonenumber_field.serializerfields import PhoneNumberField

from .models import Order, OrderItem


class OrderItemSerializer(ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderSerializer(ModelSerializer):
    phonenumber = PhoneNumberField(region="RU")
    products = OrderItemSerializer(
        many=True,
        allow_empty=False,
        write_only=True
    )

    class Meta:
        model = Order
        fields = ["id", "firstname", "lastname", "phonenumber", "address", "products"]

    def create(self, validated_data):
        products_fields = validated_data.pop("products")

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            order_items = [
                OrderItem(
                    order=order,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["product"].price
                ) for item in products_fields
            ]
            OrderItem.objects.bulk_create(order_items)

        return order

    def update(self, instance, validated_data):
        products_fields = validated_data.pop("products", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if products_fields is not None:
                instance.order_items.all().delete()
                order_items = [
                    OrderItem(
                        order=instance,
                        product=item["product"],
                        quantity=item["quantity"],
                        price=item["product"].price
                    ) for item in products_fields
                ]
                OrderItem.objects.bulk_create(order_items)

        return instance
