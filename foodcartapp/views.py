from django.db import IntegrityError
from django.http import JsonResponse
from django.templatetags.static import static
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Product, Order, OrderItem


MISSING = object()


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


def validate_products_items(products, errors: dict):

    for idx, item in enumerate(products):
        prefix = f"products[{idx}]"

        if not isinstance(item, dict):
            errors[prefix] = "Элемент должен быть объектом"
            continue

        product_id = item.get("product", MISSING)
        quantity = item.get("quantity", MISSING)

        if product_id is MISSING:
            errors[f"{prefix}.product"] = "Обязательное поле"
        elif not isinstance(product_id, int):
            errors[f"{prefix}.product"] = "Должно быть целым числом"

        if quantity is MISSING:
            errors[f"{prefix}.quantity"] = "Обязательное поле"
        elif not isinstance(quantity, int):
            errors[f"{prefix}.quantity"] = "Должно быть целым числом"
        elif quantity < 1:
            errors[f"{prefix}.quantity"] = "Должно быть ≥ 1"

    return


@api_view(['POST'])
def register_order(request):
    order_data = request.data

    firstname = order_data.get("firstname")
    lastname = order_data.get("lastname")
    phonenumber = order_data.get("phonenumber")
    address = order_data.get("address")
    products = order_data.get("products", MISSING)

    errors = {}
    if products is MISSING:
        errors["products"] = "Обязательное поле"
    elif products is None:
        errors["products"] = "Это поле не может быть пустым"
    elif not isinstance(products, list):
        errors["products"] = f"Ожидался list со значениями, но был получен {type(products).__name__}"
    elif len(products) == 0:
        errors["products"] = "Этот список не может быть пустым"
    else:
        validate_products_items(products, errors)

    if not firstname:
        errors["firstname"] = "Обязательное поле"
    if not lastname:
        errors["lastname"] = "Обязательное поле"
    if not phonenumber:
        errors["phonenumber"] = "Обязательное поле"
    if not address:
        errors["address"] = "Обязательное поле"

    if errors:
        return Response({"errors": errors}, status=400)

    try:
        order = Order.objects.create(
            firstname=order_data.get('firstname'),
            lastname=order_data.get('lastname'),
            phonenumber=order_data.get('phonenumber'),
            address=order_data.get('address'),
        )

        order_items = []
        for item in products:
            product_id = item['product']
            quantity = item['quantity']

            product = Product.objects.get(pk=product_id)
            order_items.append(OrderItem(
                order=order,
                product=product,
                quantity=quantity,
            ))

        OrderItem.objects.bulk_create(order_items)

    except Product.DoesNotExist as e:
        return Response({"error": f"Товар не найден: {e}"}, status=400)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    except IntegrityError:
        return Response({"error": "Конфликт данных"}, status=409)

    return Response({"id": order.id, "status": "created"}, status=201)
