from apify_client import ApifyClient
from django.conf import settings
import time
import json
from urllib.parse import urlparse, urljoin, parse_qs
import logging
import asyncio
import urllib.parse

logger = logging.getLogger(__name__)

class ApifyError(Exception):
    """فئة مخصصة لأخطاء Apify"""
    pass

class EcommerceScraper:
    def __init__(self):
        try:
            if not settings.APIFY_API_KEY:
                raise ApifyError("مفتاح API غير موجود في الإعدادات")
                
            self.client = ApifyClient(settings.APIFY_API_KEY)
            try:
                self.client.user().get()
                logger.info("تم التحقق من صلاحية مفتاح API بنجاح")
            except Exception as e:
                raise ApifyError(f"مفتاح API غير صالح: {str(e)}")
                
            self.max_retries = 3
            self.retry_delay = 5
                
            # تعريف المتاجر المدعومة وتفاصيلها
            self.supported_stores = {
                'amazon': {
                    'actor_id': 'junglee/amazon-crawler',
                    'base_url': 'https://www.amazon.com/s?k={query}',
                    'name': 'Amazon',
                    'memory_mb': 4096,
                    'format_mapping': {
                        'title': 'title',
                        'price': ['price', 'value'],
                        'url': 'url',
                        'image': 'thumbnailImage',
                        'rating': 'stars',
                        'reviewsCount': 'reviewsCount',
                        'description': 'description',
                        'brand': 'brand'
                    },
                    'custom_input': {
                        'maxItemsPerStartUrl': 20,
                        'scrapeProductDetails': True,
                        'country': 'US',
                        'maxConcurrency': 1,
                        'proxyConfiguration': {
                            'useApifyProxy': True,
                            'groups': ['RESIDENTIAL'],
                            'countryCode': 'US'
                        },
                        'maxRequestRetries': 2,
                        'maxRequestsPerCrawl': 30,
                        'sessionPoolName': 'amazon_pool',
                        'forceEnglish': True,
                        'timeoutSecs': 120,
                        'customMapFunction': """
                        ($) => {
                            const products = $('.s-result-item').map((i, item) => {
                                const titleEl = $(item).find('h2 a span');
                                const priceEl = $(item).find('.a-price .a-offscreen');
                                const imageEl = $(item).find('img.s-image');
                                const urlEl = $(item).find('h2 a');
                                
                                return {
                                    title: titleEl ? titleEl.text().trim() : '',
                                    price: priceEl ? priceEl.text().trim() : '',
                                    image: imageEl ? imageEl.attr('src') : '',
                                    url: urlEl ? urlEl.attr('href') : ''
                                };
                            }).get();
                            
                            return { products };
                        }
                        """
                    }
                },
                'ebay': {
                    'actor_id': 'dtrungtin/ebay-items-scraper',
                    'base_url': 'https://www.ebay.com/sch/i.html?_nkw={query}',
                    'name': 'eBay',
                    'memory_mb': 2048,
                    'format_mapping': {
                        'title': 'title',
                        'price': 'price',
                        'url': 'url',
                        'image': 'image',
                        'rating': 'rating',
                        'reviewsCount': 'reviewCount',
                        'description': 'description',
                        'condition': 'condition'
                    },
                    'custom_input': {
                        'maxItems': 1,
                        'proxyConfig': {
                            'useApifyProxy': True
                        }
                    }
                },
                
                'google_shopping': {
                    'actor_id': 'dan.scraper/google-shopping',
                    'base_url': 'https://www.google.com/shopping/search?q={query}',
                    'name': 'Google Shopping',
                    'memory_mb': 256,
                    'format_mapping': {
                        'title': 'title',
                        'price': 'price',
                        'url': 'link',
                        'image': 'image',
                        'rating': 'rating',
                        'seller': 'seller',
                        'description': 'description'
                    },
                    'custom_input': {
                        'startUrls': [],
                        'maxItems': 20,
                        'proxyConfiguration': {
                            'useApifyProxy': True,
                            'groups': ['RESIDENTIAL'],
                            'countryCode': 'US'
                        },
                        'maxConcurrency': 1,
                        'maxRequestRetries': 5,
                        'maxRequestsPerCrawl': 50,
                        'customMapFunction': """
                        ($) => {
                            const extractPrice = (el) => {
                                const price = $(el).find('.price').text().trim();
                                return price || $(el).find('[data-price]').attr('data-price');
                            };
                            
                            const products = $('.product-item').map((i, el) => {
                                return {
                                    title: $(el).find('.product-title').text().trim(),
                                    price: extractPrice(el),
                                    link: $(el).find('a').attr('href'),
                                    image: $(el).find('img').attr('src'),
                                    rating: $(el).find('.rating').text().trim(),
                                    seller: $(el).find('.seller').text().trim(),
                                    description: $(el).find('.description').text().trim()
                                };
                            }).get();
                            
                            return { products };
                        }
                        """
                    }
                },
                
                
            }

        except Exception as e:
            logger.error(f"خطأ في تهيئة EcommerceScraper: {str(e)}")
            raise ApifyError(f"فشل في تهيئة السكرابر: {str(e)}")

    def scrape_store(self, url):
        """
        استخراج المنتجات من متجر إلكتروني
        """
        try:
            if not self.is_valid_url(url):
                return {
                    'success': False,
                    'error': 'عنوان URL غير صالح',
                    'raw_data': None,
                    'status': 'فشل التحقق من صحة الرابط'
                }

            domain = urlparse(url).netloc.lower()
            if 'amazon.com' in domain:
                # تحويل الرابط إلى التنسيق المطلوب
                formatted_url = self._format_amazon_url(url)
                
                actor_id = "junglee/amazon-crawler"
                run_input = {
                    "categoryOrProductUrls": [{
                        "url": formatted_url,
                        "method": "GET"
                    }],
                    "maxItemsPerStartUrl": 20,
                    "proxyConfiguration": {
                        "useApifyProxy": True,
                        "groups": ["RESIDENTIAL"],
                        "countryCode": "US"
                    },
                    "maxConcurrency": 1,
                    "maxRequestRetries": 5,
                    "maxRequestsPerCrawl": 50,
                    "sessionPoolName": "amazon_pool",
                    "forceEnglish": True,
                    "customMapFunction": """
                    ($) => {
                        return {
                            title: $('span#productTitle').text().trim(),
                            price: $('span.a-price-whole').first().text().trim(),
                            rating: $('span.a-icon-alt').first().text().trim(),
                            reviewsCount: $('span#acrCustomerReviewText').text().trim(),
                            description: $('div#productDescription').text().trim()
                        }
                    }
                    """,
                    "scrapeProductDetails": True
                }

                try:
                    logger.info("جاري الاتصال بـ Apify...")
                    actor = self.client.actor(actor_id)
                    run = actor.call(run_input=run_input)
                    
                    logger.info("انتظار اكتمال عملية الاستخراج...")
                    run_info = actor.last_run().get()
                    
                    if not run_info:
                        logger.error("لم يتم استلام معلومات التشغيل من Apify")
                        return {
                            'success': False,
                            'error': 'فشل في الحصول على معلومات التشغيل',
                            'raw_data': None,
                            'status': 'فشل في عملية الاستخراج'
                        }

                    retry_count = 0
                    max_retries = 5
                    while run_info.get("status") not in ["SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"]:
                        time.sleep(5)
                        run_info = actor.last_run().get()
                        if not run_info:
                            break
                        logger.info(f"حالة التشغيل: {run_info.get('status', 'غير معروف')}")
                        
                        retry_count += 1
                        if retry_count >= max_retries:
                            break
                    
                    if not run_info or run_info.get("status") != "SUCCEEDED":
                        error_msg = f"فشل التشغيل: {run_info.get('status', 'غير معروف')} - يرجى المحاولة مرة أخرى"
                        logger.error(error_msg)
                        return {
                            'success': False,
                            'error': error_msg,
                            'raw_data': None,
                            'status': 'فشل في عملية الاستخراج'
                        }

                    dataset_id = run_info.get("defaultDatasetId")
                    if not dataset_id:
                        logger.error("لم يتم العثور على معرف مجموعة البيانات")
                        return {
                            'success': False,
                            'error': 'لم يتم العثور على البيانات',
                            'raw_data': None,
                            'status': 'فشل في عملية الاستخراج'
                        }

                    raw_items = list(self.client.dataset(dataset_id).iterate_items())
                    
                    logger.info(f"تم استيراد {len(raw_items)} نتيجة")
                    logger.debug(f"البيانات الخام: {raw_items}")
                    
                    formatted_items = []
                    for item in raw_items:
                        if isinstance(item, dict):
                            price_data = item.get('price', {})
                            if not isinstance(price_data, dict):
                                price_data = {}
                                
                            formatted_items.append({
                                'title': item.get('title', ''),
                                'price': price_data.get('value', ''),
                                'url': item.get('url', ''),
                                'image': item.get('thumbnailImage', ''),
                                'rating': str(item.get('stars', '')),
                                'reviewsCount': item.get('reviewsCount', ''),
                                'description': item.get('description', ''),
                                'features': item.get('features', []),
                                'availability': item.get('availability', ''),
                                'prime': item.get('prime', False),
                                'brand': item.get('brand', ''),
                                'category': item.get('breadCrumbs', ''),
                                'asin': item.get('asin', ''),
                                'bestSeller': 'Best Seller' in (item.get('badges', []) or []),
                                'originalPrice': item.get('originalPrice', {}).get('value', '')
                            })

                    return {
                        'success': True,
                        'raw_data': formatted_items,
                        'status': 'تم استخراج المنتجات بنجاح'
                    }

                except Exception as e:
                    logger.error(f"خطأ في Apify: {str(e)}")
                    return {
                        'success': False,
                        'error': str(e),
                        'raw_data': None,
                        'status': 'فشل في عملية الاستخراج'
                    }
            else:
                return {
                    'success': False,
                    'error': 'هذا المتجر غير مدعوم حالياً',
                    'raw_data': None,
                    'status': 'متجر غير مدعوم'
                }
                
        except Exception as e:
            logger.error(f"خطأ غير متوقع: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'raw_data': None,
                'status': 'حدث خطأ غير متوقع'
            }

    def _get_page_function(self):
        return """async function pageFunction(context) {
            const { request, log, page } = context;
            
            try {
                log.info('بدء البحث عن المنتجات...');
                
                // انتظار تحميل الصفحة
                await new Promise(r => setTimeout(r, 5000));
                
                // استخراج المنتجات
                const products = await page.$$eval('.s-result-item', (elements) => {
                    const results = [];
                    
                    elements.forEach((el, index) => {
                        if (index >= 20) return;
                        
                        try {
                            const name = el.querySelector('h2')?.textContent?.trim();
                            const price = el.querySelector('.a-price')?.textContent?.trim();
                            const link = el.querySelector('a[class*="a-link-normal"]')?.href;
                            const image = el.querySelector('img[class*="s-image"]')?.src;
                            
                            if (name) {
                                results.push({
                                    name,
                                    price,
                                    url: link,
                                    image,
                                    position: index + 1
                                });
                            }
                        } catch (error) {
                            console.error('Error extracting product:', error);
                        }
                    });
                    
                    return {
                        products: results,
                        totalFound: results.length,
                        url: window.location.href
                    };
                });
                
                log.info(`تم العثور على ${products.totalFound} منتج`);
                return products;
                
            } catch (error) {
                log.error(`خطأ أثناء البحث: ${error}`);
                return {
                    error: error.toString(),
                    url: request.url
                };
            }
        }"""

    def _retry_on_error(self, func, *args, **kwargs):
        """
        إعادة المحاولة في حالة حدوث أخطاء محددة
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                # التحقق من نوع الخطأ من خلال الرسالة
                error_message = str(e).lower()
                if 'rate limit' in error_message or 'service unavailable' in error_message:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (attempt + 1)
                        logger.warning(f"محاولة {attempt + 1} فشلت. انتظار {wait_time} ثواني...")
                        time.sleep(wait_time)
                continue
                raise ApifyError(f"خطأ في Apify API: {str(e)}")
        
        raise ApifyError(f"تجاوز الحد الأقصى لمحاولات إعادة المحاولة. آخر خطأ: {str(last_error)}")

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def extract_products(self, items):
        """
        تنظيف وتنسيق نتائج المنتجات
        """
        products = []
        
        for item in items:
            if not isinstance(item, dict):
                continue
                
            # تنظيف وتنسيق البيانات
            product = {
                'name': item.get('title', '').strip(),
                'price': self._clean_price(item.get('price', '')),
                'url': self._clean_url(item.get('url', '')),
                'image': self._clean_url(item.get('imageUrl', ''))
            }
            
            # إضافة المنتج فقط إذا كان لديه معلومات كافية
            if product['name'] and (product['price'] or product['url']):
                products.append(product)
                
        return products

    def _clean_price(self, price):
        """
        تنظيف وتنسيق السعر
        """
        if not price:
            return ''
            
        # إزالة الأحرف غير المرغوب فيها والاحتفاظ بالأرقام والرموز المهمة
        price = ''.join(c for c in str(price) if c.isdigit() or c in ',.$ ')
        return price.strip()

    def _clean_url(self, url):
        """
        تنظيف وتنسيق الروابط
        """
        if not url:
            return ''
            
        # تحويل الروابط النسبية إلى روابط مطلقة
        if url.startswith('//'):
            url = f'https:{url}'
        elif url.startswith('/'):
            url = urljoin('https://', url)
            
        return url.strip()

    def _collect_results(self, dataset_id):
        """
        جمع النتائج من مجموعة البيانات
        """
        try:
            items = []
            for item in self._retry_on_error(
                lambda: self.client.dataset(dataset_id).iterate_items()
            ):
                if isinstance(item, list):
                    items.extend(item)
                else:
                    items.append(item)
            return items
        except Exception as e:
            raise ApifyError(f"خطأ في استخراج النتائج: {str(e)}")

    def _format_amazon_url(self, url):
        """
        تحويل رابط Amazon إلى التنسيق المطلوب
        """
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # إذا كان الرابط يحتوي على معامل البحث k
        if 'k' in query_params:
            search_term = query_params['k'][0]
            return f"https://www.amazon.com/s?k={search_term}"
        
        # إذا كان رابط منتج
        if '/dp/' in url or '/gp/product/' in url:
            product_id = url.split('/dp/')[-1].split('/')[0] if '/dp/' in url else url.split('/gp/product/')[-1].split('/')[0]
            return f"https://www.amazon.com/dp/{product_id}"
        
        # إذا كان رابط فئة
        if '/s?' in url and ('bbn=' in url or 'rh=' in url):
            return url
        
        # إذا كان رابط عقدة
        if '/b?' in url and 'node=' in query_params:
            return url
            
        # إذا لم يكن أي من التنسيقات المعروفة، نستخرج أي نص في الرابط كمصطلح بحث
        path_parts = parsed_url.path.split('/')
        search_term = next((part for part in path_parts if part), 'electronics')
        return f"https://www.amazon.com/s?k={search_term}"

    def _validate_query(self, query):
        """
        التحقق من صحة الاستعلام قبل البحث
        """
        if not query or not isinstance(query, str):
            raise ValueError("يجب أن يكون الاستعلام نصاً غير فارغ")
        
        clean_query = query.strip()
        if len(clean_query) < 2:
            raise ValueError("يجب أن يحتوي الاستعلام على حرفين على الأقل")
        
        return clean_query

    async def scrape_multiple_stores(self, query):
        """
        استخراج المنتجات من عدة متاجر بشكل متوازي
        """
        try:
            # التحقق من صحة الاستعلام
            clean_query = self._validate_query(query)
            logger.info(f"بدء البحث عن: {clean_query}")
            
            results = []
            all_stores = list(self.supported_stores.items())
            max_memory = 8192  # 8GB
            store_groups = []
            current_group = []
            current_memory = 0
            
            # تجميع المتاجر بناءً على استهلاك الذاكرة
            for store_key, store_info in all_stores:
                store_memory = store_info.get('memory_mb', 1024)
                
                if store_memory > max_memory:
                    logger.warning(f"المتجر {store_key} يتطلب ذاكرة أكبر من الحد المسموح به")
                    continue
                    
                if current_memory + store_memory > max_memory:
                    if current_group:
                        store_groups.append(current_group)
                    current_group = [(store_key, store_info)]
                    current_memory = store_memory
                else:
                    current_group.append((store_key, store_info))
                    current_memory += store_memory
            
            if current_group:
                store_groups.append(current_group)
            
            logger.info(f"تم تقسيم المتاجر إلى {len(store_groups)} مجموعات")
            
            # معالجة كل مجموعة من المتاجر
            for group_idx, group in enumerate(store_groups, 1):
                logger.info(f"معالجة المجموعة {group_idx} من {len(store_groups)}")
                tasks = []
                
                for store_key, store_info in group:
                    logger.info(f"إضافة مهمة لمتجر {store_info['name']}")
                    task = asyncio.create_task(
                        self._scrape_single_store(store_key, store_info, clean_query)
                    )
                    tasks.append(task)
                
                # تشغيل كل المتاجر في المجموعة بشكل متوازي
                completed, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.ALL_COMPLETED
                )
                
                # معالجة النتائج المكتملة
                for task in completed:
                    try:
                        result = task.result()
                        logger.info(f"نتيجة من {result['store_name']}: {json.dumps(result, ensure_ascii=False)}")
                        
                        if result['success'] and result['raw_data']:
                            results.append(result)
                            # إرسال النتائج مباشرة
                            yield result
                        else:
                            logger.warning(f"لم يتم العثور على نتائج من {result['store_name']}: {result.get('error', 'سبب غير معروف')}")
                    
                    except Exception as e:
                        logger.error(f"خطأ في معالجة النتيجة: {str(e)}")
                
                # إلغاء المهام المعلقة
                for task in pending:
                    task.cancel()
                    logger.warning(f"تم إلغاء مهمة معلقة")
                
                # انتظار قليلاً قبل المجموعة التالية
                await asyncio.sleep(1)
            
            # التحقق من النتائج النهائية
            if not results:
                logger.warning("لم يتم العثور على أي نتائج من جميع المتاجر")
                yield {
                    'success': False,
                    'error': 'لم يتم العثور على نتائج',
                    'raw_data': [],
                    'status': 'لم يتم العثور على نتائج'
                }
            else:
                logger.info(f"تم العثور على نتائج من {len(results)} متجر")

        except Exception as e:
            logger.error(f"خطأ في استخراج المنتجات: {str(e)}")
            yield {
                'success': False,
                'error': str(e),
                'raw_data': [],
                'status': 'حدث خطأ'
            }

    async def _scrape_single_store(self, store_name, store_info, query):
        """
        استخراج البيانات من متجر واحد
        """
        if store_name not in self.supported_stores:
            logger.error(f"المتجر {store_name} غير مدعوم")
            return {
                'success': False,
                'store_name': store_name,
                'error': 'متجر غير مدعوم',
                'raw_data': []
            }

        actor_id = store_info['actor_id']
        clean_query = urllib.parse.quote(query.strip())
        search_url = store_info['base_url'].format(query=clean_query)

        try:
            # تحضير البيانات حسب المتجر
            if store_name == 'amazon':
                run_input = {
                    "categoryOrProductUrls": [{
                        "url": search_url,
                        "method": "GET"
                    }],
                    "maxItemsPerStartUrl": 20,
                    "maxOffers": 0,
                    "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
                    "scrapeProductDetails": True,
                    "scrapeProductVariantPrices": True,
                    "scrapeSellers": False,
                    "useCaptchaSolver": True
                }
            elif store_name == 'ebay':
                run_input = {
                    "maxItems": 20,
                    "proxyConfig": {
                        "useApifyProxy": True
                    },
                    "startUrls": [{
                        "url": search_url,
                        "method": "GET"
                    }]
                }
            elif store_name == 'walmart':
                run_input = {
                    "endPage": 1,
                    "extendOutputFunction": "($) => {\n    const result = {};\n    return result;\n}",
                    "includeReviews": False,
                    "maxItems": 20,
                    "onlyReviews": False,
                    "outputFilterFunction": "(object) => ({...object})",
                    "proxy": {
                        "useApifyProxy": True
                    },
                    "startUrls": [{
                        "url": search_url,
                        "method": "GET"
                    }]
                }
            elif store_name == 'google_shopping':
                run_input = {
                    "csvFriendlyOutput": False,
                    "maxPagesPerQuery": 1,
                    "queries": [query]
                }

            # تشغيل الـ actor
            actor = self.client.actor(actor_id)
            run = actor.call(
                run_input=run_input,
                memory_mbytes=store_info.get('memory_mb', 2048)
            )

            # انتظار النتائج
            for attempt in range(10):
                run_info = actor.last_run().get()
                status = run_info.get('status')
                
                if status == 'SUCCEEDED':
                    dataset_id = run_info.get('defaultDatasetId')
                    if dataset_id:
                        items = list(self.client.dataset(dataset_id).iterate_items())
                        formatted_items = self._format_store_data(items, store_info)
                        
                        return {
                            'success': True,
                            'store_name': store_info['name'],
                            'raw_data': formatted_items
                        }
                    break
                elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                    raise Exception(f"فشل التشغيل: {status}")
                
                await asyncio.sleep(3)

            return {
                'success': False,
                'store_name': store_info['name'],
                'error': 'لم يتم العثور على نتائج',
                'raw_data': []
            }

        except Exception as e:
            logger.error(f"خطأ في البحث في متجر {store_name}: {str(e)}")
            return {
                'success': False,
                'store_name': store_info['name'],
                'error': str(e),
                'raw_data': []
            }

    def _format_store_data(self, raw_data, store_info):
        """
        تنسيق البيانات حسب تعيين المتجر
        """
        formatted_data = []
        
        if not raw_data:
            return formatted_data

        store_name = store_info.get('name', '').lower()
        
        def process_image_url(url, store):
            """
            معالجة رابط الصورة حسب المتجر
            """
            if not url:
                return ''
            
            url = url.strip()
            
            if url.startswith('//'):
                url = f'https:{url}'
            
            # استخدام صور مصغرة للتحميل السريع
            if store == 'ebay':
                # استخدام الصورة المصغرة من eBay
                if 'thumbs/' not in url:
                    url = url.replace('/s-l', '/s-l200')
                return url
            elif store == 'walmart':
                # استخدام صور مصغرة من Walmart
                if 'i5.walmartimages.com' in url:
                    return f"{url.split('?')[0]}?odnHeight=200&odnWidth=200"
            elif store == 'google shopping':
                # تحسين روابط صور Google Shopping
                if 'encrypted-tbn' in url:
                    return url
                return url.split('?')[0]
            
            return url

        def extract_price(price_data):
            """
            استخراج السعر من البيانات
            """
            if not price_data:
                return ''
                
            if isinstance(price_data, dict):
                price = price_data.get('current_retail') or \
                        price_data.get('formatted_current_price') or \
                        price_data.get('price') or \
                        price_data.get('value')
                if price:
                    if isinstance(price, str):
                        price = price.replace('$', '').replace(',', '').strip()
                    try:
                        return f"${float(price):.2f}"
                    except:
                        return f"${price}"
            elif isinstance(price_data, str):
                price = price_data.replace('$', '').replace(',', '').strip()
                try:
                    return f"${float(price):.2f}"
                except:
                    return price_data
            elif isinstance(price_data, (int, float)):
                return f"${price_data:.2f}"
            return ''

        def check_availability(item, store):
            """
            التحقق من توفر المنتج
            """
            if store == 'walmart':
                stock_status = item.get('inventory', {}).get('status') or \
                             item.get('availabilityStatus') or \
                             item.get('stockStatus')
                if stock_status:
                    return stock_status.lower() in ['in_stock', 'available', 'true']
                return None
            elif store == 'ebay':
                quantity = item.get('quantity')
                if quantity is not None:
                    return int(quantity) > 0
                status = item.get('status', '').lower()
                return 'available' in status if status else None
            elif store == 'google shopping':
                availability = item.get('availability', '').lower()
                if availability:
                    return 'in stock' in availability or 'available' in availability
                return None
            elif store == 'amazon':
                status = item.get('availability', '').lower()
                if status:
                    return 'in stock' in status or 'available' in status
                return None
            return None
            
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            
            try:
                if store_name == 'google shopping':
                    # معالجة هيكل البيانات الجديد من Google Shopping
                    if 'tv' in item and isinstance(item['tv'], list):
                        for category in item['tv']:
                            if 'googleShopping' in category and isinstance(category['googleShopping'], list):
                                for product in category['googleShopping']:
                                    formatted_product = {
                                        'title': product.get('title', ''),
                                        'price': product.get('price', ''),
                                        'url': product.get('shoppingItemLink', ''),
                                        'image': process_image_url(product.get('thumbnail', ''), 'google shopping'),
                                        'rating': str(product.get('rating', '')),
                                        'reviewsCount': str(product.get('reviews', '')),
                                        'description': product.get('itemDescription', ''),
                                        'seller': product.get('itemSource', ''),
                                        'extras': product.get('extras', []),
                                        'available': True  # Google Shopping يعرض فقط المنتجات المتوفرة
                                    }
                                    if formatted_product['title'] and formatted_product['price']:
                                        formatted_data.append(formatted_product)
                    
                elif store_name == 'walmart':
                    price_info = item.get('priceInfo', {})
                    if isinstance(price_info, str):
                        try:
                            price_info = eval(price_info)
                        except:
                            price_info = {}
                            
                    product = {
                        'title': item.get('name', ''),
                        'price': extract_price(price_info.get('currentPrice', {}).get('price', '')),
                        'url': item.get('canonicalUrl', ''),
                        'image': process_image_url(item.get('imageInfo', {}).get('thumbnailUrl', '')),
                        'rating': str(item.get('averageRating', '')),
                        'reviewsCount': str(item.get('numberOfReviews', '')),
                        'description': item.get('shortDescription', ''),
                        'brand': item.get('brand', ''),
                        'available': check_availability(item, 'walmart')
                    }
                
                elif store_name == 'ebay':
                    product = {
                        'title': item.get('title', ''),
                        'price': extract_price(item.get('price', '')),
                        'url': item.get('url', ''),
                        'image': process_image_url(item.get('image', ''), 'ebay'),
                        'rating': str(item.get('rating', '')),
                        'reviewsCount': str(item.get('reviewCount', '')),
                        'description': item.get('description', ''),
                        'condition': item.get('condition', ''),
                        'available': check_availability(item, 'ebay')
                    }
                
                elif store_name == 'amazon':
                    price_value = ''
                    if isinstance(item.get('price'), dict):
                        price_value = item['price'].get('value', '')
                    elif isinstance(item.get('price'), str):
                        price_value = item['price']
                    
                    product = {
                        'title': item.get('title', ''),
                        'price': extract_price(price_value),
                        'url': item.get('url', ''),
                        'image': item.get('thumbnailImage', ''),
                        'rating': str(item.get('stars', '')),
                        'reviewsCount': str(item.get('reviewsCount', '')),
                        'description': item.get('description', ''),
                        'brand': item.get('brand', ''),
                        'available': check_availability(item, 'amazon')
                    }
                
                else:
                    for key, source in store_info['format_mapping'].items():
                        if isinstance(source, list):
                            value = item
                            for field in source:
                                value = value.get(field, {}) if isinstance(value, dict) else ''
                            product[key] = str(value)
                        else:
                            product[key] = str(item.get(source, ''))
                
                # تنظيف وتحويل البيانات
                if 'product' in locals():
                    product = {
                        key: str(value).strip() if value is not None and key != 'available' else value
                        for key, value in product.items()
                    }
                    
                    # إضافة المنتج فقط إذا كان يحتوي على معلومات أساسية
                    if product.get('title') and (product.get('price') or product.get('url')):
                        formatted_data.append(product)
                
            except Exception as e:
                logger.error(f"خطأ في معالجة منتج من {store_name}: {str(e)}")
                continue
        
        if formatted_data:
            logger.info(f"تم تنسيق {len(formatted_data)} منتج من {store_name}")
        else:
            logger.warning(f"لم يتم العثور على منتجات صالحة من {store_name}")
        
        return formatted_data 

    async def scrape_single_store(self, store_name, query):
        """
        تنفيذ البحث في متجر واحد محدد
        """
        if store_name not in self.supported_stores:
            logger.error(f"المتجر {store_name} غير مدعوم")
            return {
                'success': False,
                'store_name': store_name,
                'error': 'متجر غير مدعوم',
                'raw_data': []
            }

        store_info = self.supported_stores[store_name]
        actor_id = store_info['actor_id']
        clean_query = urllib.parse.quote(query.strip())
        search_url = store_info['base_url'].format(query=clean_query)

        try:
            # تحضير البيانات حسب المتجر
            if store_name == 'amazon':
                run_input = {
                    "categoryOrProductUrls": [{
                        "url": search_url,
                        "method": "GET"
                    }],
                    "maxItemsPerStartUrl": 20,
                    "maxOffers": 0,
                    "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
                    "scrapeProductDetails": True,
                    "scrapeProductVariantPrices": True,
                    "scrapeSellers": False,
                    "useCaptchaSolver": True
                }
            elif store_name == 'ebay':
                run_input = {
                    "maxItems": 20,
                    "proxyConfig": {
                        "useApifyProxy": True
                    },
                    "startUrls": [{
                        "url": search_url,
                        "method": "GET"
                    }]
                }
            elif store_name == 'walmart':
                run_input = {
                    "endPage": 1,
                    "extendOutputFunction": "($) => {\n    const result = {};\n    return result;\n}",
                    "includeReviews": False,
                    "maxItems": 20,
                    "onlyReviews": False,
                    "outputFilterFunction": "(object) => ({...object})",
                    "proxy": {
                        "useApifyProxy": True
                    },
                    "startUrls": [{
                        "url": search_url,
                        "method": "GET"
                    }]
                }
            elif store_name == 'google_shopping':
                run_input = {
                    "csvFriendlyOutput": False,
                    "maxPagesPerQuery": 1,
                    "queries": [query]
                }

            # تشغيل الـ actor
            actor = self.client.actor(actor_id)
            run = actor.call(
                run_input=run_input,
                memory_mbytes=store_info.get('memory_mb', 2048)
            )

            # انتظار النتائج
            for attempt in range(10):
                run_info = actor.last_run().get()
                status = run_info.get('status')
                
                if status == 'SUCCEEDED':
                    dataset_id = run_info.get('defaultDatasetId')
                    if dataset_id:
                        items = list(self.client.dataset(dataset_id).iterate_items())
                        formatted_items = self._format_store_data(items, store_info)
                        
                        return {
                            'success': True,
                            'store_name': store_info['name'],
                            'raw_data': formatted_items
                        }
                    break
                elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                    raise Exception(f"فشل التشغيل: {status}")
                
                await asyncio.sleep(3)

            return {
                'success': False,
                'store_name': store_info['name'],
                'error': 'لم يتم العثور على نتائج',
                'raw_data': []
            }

        except Exception as e:
            logger.error(f"خطأ في البحث في متجر {store_name}: {str(e)}")
            return {
                'success': False,
                'store_name': store_info['name'],
                'error': str(e),
                'raw_data': []
            } 