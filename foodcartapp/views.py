from django.http import JsonResponse
from django.templatetags.static import static
import json

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


def register_order(request):
    order_data = json.loads(request.body.decode())

    order = Order.objects.create(
        firstname=order_data.get('firstname'),
        lastname=order_data.get('lastname'),
        phonenumber=order_data.get('phonenumber'),
        address=order_data.get('address'),
    )

    order_items = []
    for item in order_data.get('products'):
        product_id = item.get('product')
        quantity = item.get('quantity')

        product = Product.objects.get(pk=product_id)
        order_items.append(OrderItem(
            order=order,
            product=product,
            quantity=quantity,
        ))

    OrderItem.objects.bulk_create(order_items)

    return JsonResponse({"id": order.id, "status": "created"}, status=201)
