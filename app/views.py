from django.contrib.auth import authenticate, login  
from .forms import CustomUserCreationForm 
from django.shortcuts import get_object_or_404, render, redirect 
from .models import Product
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages 
from .forms import AddToCartForm 
import json  
import requests 
from .models import Sale 
from .forms import PurchaseForm

def index(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'app/index.html', {'products': products})

def signup(request):
    if request.method == 'POST':
       form = CustomUserCreationForm(request.POST)
       if form.is_valid():
           new_user = form.save()
           input_email = form.cleaned_data['email']
           input_password = form.cleaned_data['password1']
           new_user = authenticate(email=input_email,
password=input_password)
           if new_user is not None:
               login(request, new_user)
               return redirect('app:index')
    else:
       form = CustomUserCreationForm()
    return render(request, 'app/signup.html', {'form': form})

def detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    add_to_cart_form = AddToCartForm(request.POST or None)
    if add_to_cart_form.is_valid():
       num = add_to_cart_form.cleaned_data['num']

       # セッションに cart というキーがあるかどうかで処理を分ける 
       if 'cart' in request.session:
           # すでに特定の商品の個数があれば新しい個数を加算、なければ新しくキ ーを追加する
           if str(product_id) in request.session['cart']:
               request.session['cart'][str(product_id)] += num
           else:
               request.session['cart'][str(product_id)] = num
       else:
         # 新しく cart というセッションのキーを追加 
         request.session['cart'] = {str(product_id): num}
       messages.success(request, f"{product.name}を{num}個カートに入れました!")
       return redirect('app:detail', product_id=product_id)
    context = {
       'product': product,
       'add_to_cart_form': add_to_cart_form,
    }

    return render(request, 'app/detail.html', context)

@login_required
@require_POST
def toggle_fav_product_status(request):
    product = get_object_or_404(Product, pk=request.POST["product_id"])
    user = request.user
    if product in user.fav_products.all():
       user.fav_products.remove(product)
    else:
       user.fav_products.add(product)
    return redirect('app:detail', product_id=product.id)

@login_required
def fav_products(request):
    user = request.user
    products = user.fav_products.all()
    return render(request, 'app/index.html', {'products': products})

@login_required
def cart(request):
    user = request.user
    cart = request.session.get('cart', {})
    cart_products = dict()
    total_price = 0
    for product_id, num in cart.items():
       product = Product.objects.get(id=product_id)
       cart_products[product] = num
       total_price += product.price * num
    
    purchase_form = PurchaseForm(request.POST or None)
    if purchase_form.is_valid():
      # 住所検索ボタンが押された場合
      if 'search_address' in request.POST:
        zip_code = request.POST['zip_code']
        address = get_address(zip_code)
        # 住所が取得できなかった場合はメッセージを出してリダイレクト
        if not address:
          messages.warning(request, "住所を取得できませんでした。")
          return redirect('app:cart')
        # 住所が取得できたらフォームに入力してあげる
        purchase_form = PurchaseForm(initial={'zip_code': zip_code,'address': address})
      
      # 購入ボタンが押された場合
      if 'buy_product' in request.POST:
        # 住所が入力済みか確認する
        if not purchase_form.cleaned_data['address']:
          messages.warning(request, "住所の入力は必須です")
          return redirect('app:cart')
        # カートが空じゃないか確認
        if not bool(cart):
          messages.warning(request, "カートは空です")
          return redirect('app:cart')
        # 所持ポイントが十分にあるか確認
        if total_price > user.point:
          messages.warning(request, "所持ポイントが足りません")
          return redirect('app:cart')

        # 各プロダクトの Sale 情報を保存
        for product_id, num in cart.items():
          if not Product.objects.filter(pk=product_id).exists():
            del cart[product_id]
          product = Product.objects.get(pk=product_id)
          sale = Sale(product=product, user=request.user,amount=num, price=product.price, total_price=num*product.price)
          sale.save()
        # ポイントを削減
        user.point -= total_price
        user.save()
        del request.session['cart']
        messages.success(request, "商品の購入が完了しました!")
        return redirect('app:cart')
    
    context = {
      'purchase_form': purchase_form,
      'cart_products': cart_products,
      'total_price': total_price
    }
    return render(request, 'app/cart.html', context)

@login_required
@require_POST
def change_item_amount(request):
    product_id = request.POST["product_id"]
    cart_session = request.session['cart']
    if product_id in cart_session:
       if 'action_remove' in request.POST:
           cart_session[product_id] -= 1
       if 'action_add' in request.POST:
           cart_session[product_id] += 1
       if cart_session[product_id] <= 0:
           del cart_session[product_id]
    return redirect('app:cart')

def get_address(zip_code):
    REQUEST_URL = f'http://zipcloud.ibsnet.co.jp/api/search?zipcode={zip_code}'
    address = ''
    response = requests.get(REQUEST_URL)
    response = json.loads(response.text)
    result, api_status = response['results'], response['status']
    if api_status == 200:
       result = result[0]
       address = result['address1'] + result['address2'] + result['address3']
    return address
@login_required
def order_history(request):
    user = request.user
    sales = Sale.objects.filter(user=user).order_by('-created_at')
    return render(request, 'app/order_history.html', {'sales': sales})