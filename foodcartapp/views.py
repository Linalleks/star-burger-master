from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from phonenumber_field.serializerfields import PhoneNumberField

from .models import Product, Order, OrderItem


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


class OrderItemSerializer(ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderSerializer(ModelSerializer):
    phonenumber = PhoneNumberField(region="RU")
    products = OrderItemSerializer(
        many=True,
        allow_empty=False,
    )

    class Meta:
        model = Order
        fields = ["firstname", "lastname", "phonenumber", "address", "products"]


@api_view(['POST'])
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    order_fields = serializer.validated_data

    order = Order.objects.create(
        firstname=order_fields["firstname"],
        lastname=order_fields["lastname"],
        phonenumber=order_fields["phonenumber"],
        address=order_fields["address"],
    )

    products_fields = order_fields['products']
    order_items = [
        OrderItem(
            order=order,
            product=item["product"],
            quantity=item["quantity"]
            ) for item in products_fields
        ]
    OrderItem.objects.bulk_create(order_items)

    return Response({"id": order.id, "status": "created"}, status=201)
