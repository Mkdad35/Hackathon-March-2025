from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
import requests
from django.conf import settings
import cohere
from .models import Store
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from .scraper import EcommerceScraper, ApifyError
import logging
import json
import asyncio
import base64
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# Create your views here.

def search_view(request):
    return render(request, 'core/search.html')

# المتاجر العالمية حسب التصنيف
GLOBAL_STORES = {
    "Fashion & Accessories": [
        {
            "name": "ASOS",
            "url": "https://www.asos.com",
            "categories": "Fashion, Clothing, Shoes, Accessories",
            "shipping": "International shipping available"
        },
        {
            "name": "SHEIN",
            "url": "https://www.shein.com",
            "categories": "Fashion, Clothing, Accessories",
            "shipping": "Worldwide shipping"
        },
        {
            "name": "Farfetch",
            "url": "https://www.farfetch.com",
            "categories": "Luxury Fashion, Designer Brands",
            "shipping": "Global shipping"
        },
        {
            "name": "Zalando",
            "url": "https://www.zalando.com",
            "categories": "Fashion, Shoes, Accessories",
            "shipping": "European shipping"
        },
        {
            "name": "Net-a-Porter",
            "url": "https://www.net-a-porter.com",
            "categories": "Luxury Fashion, Designer Wear",
            "shipping": "Global shipping"
        }
    ],
    "Electronics & Technology": [
        {
            "name": "Amazon",
            "url": "https://www.amazon.com",
            "categories": "Electronics, Gadgets, Everything",
            "shipping": "International shipping on eligible items"
        },
        {
            "name": "Newegg",
            "url": "https://www.newegg.com",
            "categories": "Electronics, PC Components, Gaming",
            "shipping": "International shipping"
        },
        {
            "name": "AliExpress",
            "url": "https://www.aliexpress.com",
            "categories": "Electronics, Gadgets, Various items",
            "shipping": "Worldwide shipping"
        },
        {
            "name": "B&H Photo Video",
            "url": "https://www.bhphotovideo.com",
            "categories": "Electronics, Cameras, Audio",
            "shipping": "International shipping"
        }
    ],
    "Beauty & Cosmetics": [
        {
            "name": "Sephora",
            "url": "https://www.sephora.com",
            "categories": "Beauty, Skincare, Perfumes",
            "shipping": "Available in many countries"
        },
        {
            "name": "iHerb",
            "url": "https://www.iherb.com",
            "categories": "Beauty, Health, Supplements",
            "shipping": "Global shipping"
        },
        {
            "name": "Cult Beauty",
            "url": "https://www.cultbeauty.com",
            "categories": "Beauty, Skincare, Makeup",
            "shipping": "International shipping"
        },
        {
            "name": "Lookfantastic",
            "url": "https://www.lookfantastic.com",
            "categories": "Beauty, Skincare, Hair Care",
            "shipping": "Global shipping"
        }
    ],
    "Sports & Fitness": [
        {
            "name": "Nike",
            "url": "https://www.nike.com",
            "categories": "Sports Wear, Shoes, Equipment",
            "shipping": "International shipping"
        },
        {
            "name": "Adidas",
            "url": "https://www.adidas.com",
            "categories": "Sports Wear, Shoes, Accessories",
            "shipping": "Global shipping"
        },
        {
            "name": "Under Armour",
            "url": "https://www.underarmour.com",
            "categories": "Sports Wear, Athletic Gear",
            "shipping": "International shipping"
        },
        {
            "name": "Gymshark",
            "url": "https://www.gymshark.com",
            "categories": "Fitness Wear, Gym Equipment",
            "shipping": "Worldwide shipping"
        }
    ],
    "Home & Garden": [
        {
            "name": "Wayfair",
            "url": "https://www.wayfair.com",
            "categories": "Furniture, Home Decor, Garden",
            "shipping": "International shipping available"
        },
        {
            "name": "IKEA",
            "url": "https://www.ikea.com",
            "categories": "Furniture, Home Accessories",
            "shipping": "Available in many countries"
        },
        {
            "name": "Pottery Barn",
            "url": "https://www.potterybarn.com",
            "categories": "Furniture, Home Decor",
            "shipping": "Select countries"
        }
    ],
    "Books & Stationery": [
        {
            "name": "Book Depository",
            "url": "https://www.bookdepository.com",
            "categories": "Books, Free worldwide delivery",
            "shipping": "Free worldwide shipping"
        },
        {
            "name": "Barnes & Noble",
            "url": "https://www.barnesandnoble.com",
            "categories": "Books, Magazines, Stationery",
            "shipping": "International shipping"
        }
    ],
    "Toys & Games": [
        {
            "name": "Toys R Us",
            "url": "https://www.toysrus.com",
            "categories": "Toys, Games, Baby Products",
            "shipping": "Select countries"
        },
        {
            "name": "The Lego Shop",
            "url": "https://www.lego.com",
            "categories": "LEGO Sets, Toys",
            "shipping": "Global shipping"
        }
    ],
    "Automotive": [
        {
            "name": "AutoZone",
            "url": "https://www.autozone.com",
            "categories": "Auto Parts, Accessories",
            "shipping": "Select countries"
        },
        {
            "name": "RockAuto",
            "url": "https://www.rockauto.com",
            "categories": "Auto Parts, Tools",
            "shipping": "International shipping"
        }
    ],
    "Pet Supplies": [
        {
            "name": "Chewy",
            "url": "https://www.chewy.com",
            "categories": "Pet Food, Supplies",
            "shipping": "US shipping"
        },
        {
            "name": "PetSmart",
            "url": "https://www.petsmart.com",
            "categories": "Pet Supplies, Food",
            "shipping": "Select regions"
        }
    ],
    "Luxury & Watches": [
        {
            "name": "Chrono24",
            "url": "https://www.chrono24.com",
            "categories": "Luxury Watches",
            "shipping": "Worldwide shipping"
        },
        {
            "name": "Jomashop",
            "url": "https://www.jomashop.com",
            "categories": "Watches, Luxury Items",
            "shipping": "International shipping"
        }
    ],
    "Music & Instruments": [
        {
            "name": "Thomann",
            "url": "https://www.thomann.de",
            "categories": "Musical Instruments, Equipment",
            "shipping": "Worldwide shipping"
        },
        {
            "name": "Sweetwater",
            "url": "https://www.sweetwater.com",
            "categories": "Musical Instruments, Pro Audio",
            "shipping": "International shipping"
        }
    ]
}

def format_store_data(stores_dict):
    formatted_text = ""
    for category, stores in stores_dict.items():
        formatted_text += f"\n{category}:\n{'='*50}\n"
        for store in stores:
            formatted_text += f"""
Store Name: {store['name']}
URL: {store['url']}
Categories: {store['categories']}
Shipping: {store['shipping']}
{'-'*50}
"""
    return formatted_text

def get_ecommerce_sites(request):
    if request.method == 'POST':
        country = request.POST.get('country_name')
        print(f"\nSearching e-commerce sites for: {country}")
        
        try:
            # البحث عن المتاجر في قاعدة البيانات
            stores = Store.objects.filter(country=country)
            
            if stores.exists():
                # تنظيم المتاجر حسب التصنيف
                formatted_text = ""
                categories = {}
                
                for store in stores:
                    category = store.get_category_display()  # الحصول على النص الوصفي للتصنيف
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(store)
                
                # تنسيق النص للعرض
                for category, store_list in categories.items():
                    formatted_text += f"\n{category}:\n{'='*50}\n"
                    for store in store_list:
                        formatted_text += f"""
Store Name: {store.name}
URL: {store.url}
Shipping: {store.shipping_info}
{'-'*50}
"""
                
                return JsonResponse({
                    'success': True,
                    'data': formatted_text
                })
            else:
                # إذا لم نجد متاجر، نستخدم المتاجر العالمية
                formatted_text = format_store_data(GLOBAL_STORES)
                return JsonResponse({
                    'success': True,
                    'data': formatted_text
                })
                
        except Exception as e:
            error_message = f'Error: {str(e)}'
            print(f"\nError occurred: {error_message}")
            return JsonResponse({
                'success': False,
                'error': error_message
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def collect_stores(request):
    if request.method == 'POST':
        country = request.POST.get('country_name')
        
        try:
            # استخدام Cohere للحصول على معلومات المتاجر
            co = cohere.Client(settings.COHERE_API_KEY)
            prompt = f"""List the most popular and reliable online shopping websites for {country}.
            For each store, provide:
            1. Store name
            2. Website URL (with https://)
            3. Main category (one of: Fashion & Accessories, Electronics & Technology, Beauty & Cosmetics, 
               Sports & Fitness, Home & Garden, Books & Stationery, Toys & Games, Automotive, Pet Supplies, 
               Luxury & Watches, Music & Instruments)
            4. Shipping information
            
            Format each store as:
            Name: [store name]
            URL: [url]
            Category: [category]
            Shipping: [shipping info]
            ---"""
            
            response = co.generate(
                model='command',
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7,
                stop_sequences=["---"],
                return_likelihoods='NONE'
            )
            
            # تحليل النص المُنتج
            stores_data = []
            current_store = {}
            
            for line in response.generations[0].text.split('\n'):
                line = line.strip()
                if line.startswith('Name:'):
                    if current_store:
                        stores_data.append(current_store)
                    current_store = {'country': country}
                    current_store['name'] = line.replace('Name:', '').strip()
                elif line.startswith('URL:'):
                    current_store['url'] = line.replace('URL:', '').strip()
                elif line.startswith('Category:'):
                    category = line.replace('Category:', '').strip()
                    # تحويل النص إلى رمز التصنيف
                    category_map = {choice[1]: choice[0] for choice in Store.CATEGORY_CHOICES}
                    current_store['category'] = category_map.get(category, 'fashion')
                elif line.startswith('Shipping:'):
                    current_store['shipping_info'] = line.replace('Shipping:', '').strip()
            
            if current_store:
                stores_data.append(current_store)
            
            # حفظ في قاعدة البيانات
            for store_data in stores_data:
                Store.objects.get_or_create(
                    name=store_data['name'],
                    country=store_data['country'],
                    defaults={
                        'url': store_data['url'],
                        'category': store_data['category'],
                        'shipping_info': store_data['shipping_info']
                    }
                )
            
            # تحديث ملف Excel
            all_stores = Store.objects.all()
            df = pd.DataFrame(list(all_stores.values()))
            excel_path = 'stores_database.xlsx'
            df.to_excel(excel_path, index=False)
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully collected stores for {country}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

async def scrape_stores(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_query = data.get('query', '').strip()
            
            if not product_query:
                return JsonResponse({
                    'success': False,
                    'error': 'يرجى إدخال المنتج المراد البحث عنه'
                })
            
            # تحسين الاستعلام باستخدام Cohere
            enhanced_query_data = {}
            try:
                enhanced_query_data = await enhance_query_with_ai(product_query)
                optimized_query = enhanced_query_data.get('keywords', product_query)
                category = enhanced_query_data.get('category', 'general')
                logger.info(f"تم تحسين الاستعلام: '{optimized_query}', الفئة: {category}")
                # استخدام الاستعلام المحسن للبحث
                product_query = optimized_query
            except Exception as e:
                logger.error(f"خطأ في تحسين الاستعلام: {str(e)}")
                # في حالة فشل تحسين الاستعلام، استمر بالاستعلام الأصلي

            scraper = EcommerceScraper()
            
            async def generate_results():
                stores = ['amazon', 'ebay', 'google_shopping']
                
                # إرسال معلومات تحسين الاستعلام أولاً
                if enhanced_query_data:
                    query_info = {
                        'success': True,
                        'type': 'query_info',
                        'enhanced_query': enhanced_query_data
                    }
                    yield f"data: {json.dumps(query_info)}\n\n"
                
                for store in stores:
                    try:
                        result = await scraper.scrape_single_store(store, product_query)
                        if result and isinstance(result, dict):
                            # تحقق من وجود المنتجات في raw_data
                            products = result.get('raw_data', [])
                            if products:
                                formatted_result = {
                                    'success': True,
                                    'store_name': store,
                                    'products': products,
                                    'enhanced_query': enhanced_query_data
                                }
                                yield f"data: {json.dumps(formatted_result)}\n\n"
                                logger.info(f"تم العثور على {len(products)} منتج من {store}")
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"خطأ في البحث في متجر {store}: {str(e)}")
                        yield f"data: {json.dumps({'success': False, 'store_name': store, 'error': str(e)})}\n\n"
            
            response = StreamingHttpResponse(
                generate_results(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'تنسيق البيانات غير صحيح'
            })
        except Exception as e:
            logger.error(f"خطأ في عملية الاستخراج: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'طريقة طلب غير صالحة'
    })

async def enhance_query_with_ai(query):
    """
    تحسين استعلام البحث باستخدام Cohere AI
    1. ترجمة الاستعلام إلى الإنجليزية (إذا كان بلغة أخرى)
    2. تصحيح الأخطاء الإملائية
    3. استخراج الكلمات المفتاحية الأكثر فعالية للبحث
    4. تحديد فئة المنتج
    """
    try:
        # تحسين مبدئي للاستعلام قبل إرساله إلى Cohere
        # معالجة حالات مثل "the name of the film is X" للتركيز على "X"
        processed_query = query
        common_patterns = [
            (r'the name of the (\w+) is (.+)', r'\2 \1'),  # "the name of the film is sneakers" -> "sneakers film"
            (r'looking for (\w+) called (.+)', r'\2 \1'),  # "looking for a book called X" -> "X book"
            (r'searching for (\w+) named (.+)', r'\2 \1'), # "searching for product named X" -> "X product"
            (r'find me a (\w+) titled (.+)', r'\2 \1'),    # "find me a movie titled X" -> "X movie"
            (r'i want to buy (.+)', r'\1'),                # "i want to buy X" -> "X"
            (r'i need to find (.+)', r'\1'),               # "i need to find X" -> "X"
        ]
        
        import re
        for pattern, replacement in common_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                processed_query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
                logger.info(f"معالجة الاستعلام: من '{query}' إلى '{processed_query}'")
                break
                
        co = cohere.Client(settings.COHERE_API_KEY)
        
        prompt = f"""As a smart product search assistant, help analyze this product query:
"{processed_query}"

Pay special attention to product names and treat them as exact search terms, not keywords to extract.
For example, if the input mentions "sneakers" as a movie title, don't treat it as footwear.

1. TRANSLATE: If this query is not in English, translate it to English.
2. FIX: Fix any spelling errors and improve the wording for search.
3. KEYWORDS: Extract the main product terms optimized for e-commerce search (2-5 words only). If the query appears to be about a specific named product, include that full product name.
4. CATEGORY: Categorize the product into one of these categories: [Electronics, Fashion, Home, Beauty, Sports, Toys, Books, Automotive, Grocery, Other].

Format your answer exactly like this:
```
Translated: [translated text]
Fixed: [corrected text]
Keywords: [keywords for search]
Category: [category]
```
"""
        
        response = co.generate(
            model='command',
            prompt=prompt,
            max_tokens=500,
            temperature=0.2,
        )
        
        result = response.generations[0].text.strip()
        result_data = {}
        
        # استخراج المعلومات من النص
        sections = result.split("```")[1].strip() if "```" in result else result
        
        for line in sections.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == "translated":
                    result_data['translated'] = value
                elif key == "fixed":
                    result_data['fixed'] = value
                elif key == "keywords":
                    result_data['keywords'] = value
                elif key == "category":
                    result_data['category'] = value.lower()
        
        # إضافة الاستعلام الأصلي والمعالج للنتيجة
        result_data['original_query'] = query
        result_data['processed_query'] = processed_query
        
        return result_data
    
    except Exception as e:
        logger.error(f"Error in enhance_query_with_ai: {str(e)}")
        # Return an empty dict in case of error
        return {}

def solo_scrape(request):
    if request.method == 'POST':
        store_url = request.POST.get('store_url')
        
        if not store_url:
            return JsonResponse({
                'success': False,
                'error': 'يرجى إدخال رابط المتجر',
                'status': 'بيانات غير مكتملة'
            })
            
        try:
            scraper = EcommerceScraper()
            result = scraper.scrape_store(store_url)
            
            # تأكد من أن النتيجة تحتوي على raw_data
            if result['success'] and 'raw_data' not in result:
                result['raw_data'] = []
                
            return JsonResponse(result)
                
        except ApifyError as e:
            logger.error(f"خطأ Apify: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e),
                'status': 'خطأ في خدمة Apify'
            })
        except Exception as e:
            logger.error(f"خطأ غير متوقع: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ غير متوقع',
                'status': 'خطأ في النظام'
            })
            
    return JsonResponse({
        'success': False,
        'error': 'طريقة طلب غير صالحة',
        'status': 'خطأ في الطلب'
    })

def product_details(request, product_data):
    try:
        # فك تشفير البيانات
        decoded_data = base64.b64decode(product_data).decode('utf-8')
        decoded_data = unquote(decoded_data)  # فك تشفير URI
        product = json.loads(decoded_data)
        return render(request, 'core/product_details.html', {'product': product})
    except Exception as e:
        logger.error(f"Error decoding product data: {str(e)}")
        return redirect('core:search')

def home(request):
    return render(request, 'core/home.html')
