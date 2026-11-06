from django.db import IntegrityError
from django.http import JsonResponse
from django.templatetags.static import static
from phonenumber_field.phonenumber import PhoneNumber
from phonenumber_field.validators import validate_international_phonenumber
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
    
    valid_items = 0

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

        if f"{prefix}.product" not in errors and f"{prefix}.quantity" not in errors:
            valid_items += 1

    return valid_items == len(products)


def validate_products_exist(products, errors: dict):
    products_ids = [item["product"] for item in products]
    products_map = Product.objects.in_bulk(products_ids)
    products_ok = True

    for id in products_ids:
        if id not in products_map:
            errors[f"products[product={id}]"] = f"Недопустимый первичный ключ {id}"
            products_ok = False

    if not products_ok:
        return products_ok

    return products_map


def validate_required_str(value, errors: dict, key: str) -> None:
    if value is MISSING:
        errors[key] = "Обязательное поле"
    elif value is None:
        errors[key] = "Это поле не может быть пустым"
    elif not isinstance(value, str):
        errors[key] = f"Ожидалась строка, но был получен {type(value).__name__}"
    elif not value.strip():
        errors[key] = "Это поле не может быть пустым или состоять из одних пробелов"


@api_view(['POST'])
def register_order(request):
    order_data = request.data

    firstname = order_data.get("firstname", MISSING)
    lastname = order_data.get("lastname", MISSING)
    phonenumber = order_data.get("phonenumber", MISSING)
    address = order_data.get("address", MISSING)
    products = order_data.get("products", MISSING)

    errors = {}
    if products is MISSING:
        errors["products"] = "Обязательное поле"
    elif products is None:
        errors["products"] = "Это поле не может быть пустым"
    elif not isinstance(products, list):
        errors["products"] = ("Ожидался list со значениями, "
                              f"но был получен {type(products).__name__}")
    elif len(products) == 0:
        errors["products"] = "Этот список не может быть пустым"
    elif validate_products_items(products, errors):
        products_map = validate_products_exist(products, errors)

    validate_required_str(firstname, errors, "firstname")
    validate_required_str(lastname, errors, "lastname")
    validate_required_str(address, errors, "address")
    validate_required_str(phonenumber, errors, "phonenumber")
    if "phonenumber" not in errors:
        try:
            phone = PhoneNumber.from_string(phonenumber, region="RU")
        except Exception:
            errors["phonenumber"] = "Введен некорректный номер телефона"
        if not phone.is_valid():
            errors["phonenumber"] = "Введен некорректный номер телефона"

    if errors:
        return Response({"errors": errors}, status=400)

    try:
        order = Order.objects.create(
            firstname=firstname.strip(),
            lastname=lastname.strip(),
            phonenumber=phonenumber.strip(),
            address=address.strip(),
        )

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=products_map[item["product"]],
                quantity=item["quantity"],
            )
            for item in products
        ])

    except Product.DoesNotExist as e:
        return Response({"error": f"Товар не найден: {e}"}, status=400)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    except IntegrityError:
        return Response({"error": "Конфликт данных"}, status=409)

    return Response({"id": order.id, "status": "created"}, status=201)
