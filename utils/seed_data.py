"""Seeds the database with a 40-item specialty-coffee shop catalog.

Idempotent: skips seeding if products already exist.
"""
from __future__ import annotations

from database import Database

CATEGORIES: dict[str, str] = {
    "Hot Coffee Drinks": "☕",
    "Cold Coffee": "🧊",
    "Tea & Other": "🍵",
    "Pastries & Desserts": "🥐",
    "Single Origin Beans": "🌱",
    "Espresso Blends": "🫘",
    "Brewing Equipment": "⚙️",
    "Accessories": "🎁",
}

PRODUCTS: list[dict] = [
    # ── Hot Coffee Drinks ────────────────────────────────────────────────
    {
        "category": "Hot Coffee Drinks",
        "name": "Espresso",
        "description": (
            "A single 30 ml shot pulled from our house blend. "
            "Thick golden crema, syrupy body, notes of dark chocolate and toasted hazelnut."
        ),
        "price": 3.50,
        "photo_url": "assets/photos/01_espresso.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Doppio",
        "description": (
            "Double espresso for serious mornings. Two shots, 60 ml total, "
            "intense and full-bodied with a rich crema."
        ),
        "price": 4.50,
        "photo_url": "assets/photos/02_doppio.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Americano",
        "description": (
            "A double espresso lengthened with hot water — clean, smooth and aromatic. "
            "Served at 240 ml."
        ),
        "price": 4.00,
        "photo_url": "assets/photos/03_americano.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Cappuccino",
        "description": (
            "Italian classic: equal parts espresso, steamed milk and silky foam. "
            "Topped with a delicate rosetta latte art."
        ),
        "price": 4.80,
        "photo_url": "assets/photos/04_cappuccino.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Caffè Latte",
        "description": (
            "Smooth and creamy: one espresso shot stretched with steamed milk and "
            "a thin layer of velvety microfoam. 350 ml."
        ),
        "price": 5.20,
        "photo_url": "assets/photos/05_latte.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Flat White",
        "description": (
            "Antipodean favourite — double ristretto with steamed milk and "
            "paper-thin microfoam. Coffee-forward, no sugar needed."
        ),
        "price": 5.00,
        "photo_url": "assets/photos/06_flat_white.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Mocha",
        "description": (
            "Espresso, dark Belgian chocolate and steamed milk, finished with whipped cream "
            "and a dusting of cocoa. The dessert in a cup."
        ),
        "price": 5.80,
        "photo_url": "assets/photos/07_mocha.jpg",
    },
    {
        "category": "Hot Coffee Drinks",
        "name": "Caramel Macchiato",
        "description": (
            "Layered drink: vanilla, steamed milk, espresso and a swirl of caramel sauce. "
            "Sweet, balanced, indulgent."
        ),
        "price": 5.50,
        "photo_url": "assets/photos/08_macchiato.jpg",
    },
    # ── Cold Coffee ──────────────────────────────────────────────────────
    {
        "category": "Cold Coffee",
        "name": "Iced Latte",
        "description": (
            "Double espresso poured over cold milk and ice. Refreshing, balanced, "
            "served in a 400 ml glass."
        ),
        "price": 5.40,
        "photo_url": "assets/photos/09_iced_latte.jpg",
    },
    {
        "category": "Cold Coffee",
        "name": "Iced Americano",
        "description": (
            "Two espresso shots over ice and chilled water. Clean, crisp, "
            "low-calorie pick-me-up."
        ),
        "price": 4.50,
        "photo_url": "assets/photos/10_iced_americano.jpg",
    },
    {
        "category": "Cold Coffee",
        "name": "Cold Brew",
        "description": (
            "Coarsely ground beans steeped in cold water for 18 hours. "
            "Naturally sweet, low-acid, served black over ice."
        ),
        "price": 5.20,
        "photo_url": "assets/photos/11_cold_brew.jpg",
    },
    {
        "category": "Cold Coffee",
        "name": "Nitro Cold Brew",
        "description": (
            "Cold brew infused with nitrogen on tap. Cascading creamy head, "
            "silky texture, no sugar or milk required."
        ),
        "price": 6.20,
        "photo_url": "assets/photos/12_nitro_cold_brew.jpg",
    },
    {
        "category": "Cold Coffee",
        "name": "Coffee Frappé",
        "description": (
            "Blended iced coffee with milk, ice and a touch of sugar, "
            "topped with whipped cream and chocolate drizzle."
        ),
        "price": 6.00,
        "photo_url": "assets/photos/13_frappe.jpg",
    },
    {
        "category": "Cold Coffee",
        "name": "Affogato",
        "description": (
            "A scoop of vanilla bean gelato \"drowned\" in a fresh hot espresso. "
            "Italian dessert and coffee in one."
        ),
        "price": 6.50,
        "photo_url": "assets/photos/14_affogato.jpg",
    },
    # ── Tea & Other ──────────────────────────────────────────────────────
    {
        "category": "Tea & Other",
        "name": "English Breakfast Tea",
        "description": (
            "Robust black tea blend, malty and full-bodied. Served with a slice of lemon "
            "or a splash of milk, your choice."
        ),
        "price": 3.80,
        "photo_url": "assets/photos/15_black_tea.jpg",
    },
    {
        "category": "Tea & Other",
        "name": "Sencha Green Tea",
        "description": (
            "Premium Japanese sencha — vegetal, sweet and grassy. "
            "Brewed at 75 °C to preserve delicate flavour."
        ),
        "price": 4.20,
        "photo_url": "assets/photos/16_green_tea.jpg",
    },
    {
        "category": "Tea & Other",
        "name": "Matcha Latte",
        "description": (
            "Ceremonial-grade matcha whisked with steamed milk. Earthy, vibrant green, "
            "rich in antioxidants. Available hot or iced."
        ),
        "price": 5.50,
        "photo_url": "assets/photos/17_matcha_latte.jpg",
    },
    {
        "category": "Tea & Other",
        "name": "Masala Chai Latte",
        "description": (
            "House-made chai concentrate with cardamom, cinnamon, ginger and clove, "
            "stretched with steamed milk. Spicy and warming."
        ),
        "price": 5.20,
        "photo_url": "assets/photos/18_chai_latte.jpg",
    },
    {
        "category": "Tea & Other",
        "name": "Hot Chocolate",
        "description": (
            "Belgian dark chocolate melted into steamed whole milk, finished with "
            "marshmallows and cocoa powder."
        ),
        "price": 5.00,
        "photo_url": "assets/photos/19_hot_chocolate.jpg",
    },
    # ── Pastries & Desserts ──────────────────────────────────────────────
    {
        "category": "Pastries & Desserts",
        "name": "Butter Croissant",
        "description": (
            "Hand-laminated 27-layer croissant baked fresh every morning. "
            "Crisp, flaky, buttery — best with espresso."
        ),
        "price": 4.20,
        "photo_url": "assets/photos/20_croissant.jpg",
    },
    {
        "category": "Pastries & Desserts",
        "name": "Pain au Chocolat",
        "description": (
            "Two batons of dark Valrhona chocolate wrapped in our buttery laminated dough. "
            "Warmed on request."
        ),
        "price": 4.80,
        "photo_url": "assets/photos/21_pain_au_chocolat.jpg",
    },
    {
        "category": "Pastries & Desserts",
        "name": "New York Cheesecake",
        "description": (
            "Classic baked cheesecake on a graham crust, topped with house-made "
            "strawberry coulis. Slice 120 g."
        ),
        "price": 6.50,
        "photo_url": "assets/photos/22_cheesecake.jpg",
    },
    {
        "category": "Pastries & Desserts",
        "name": "Tiramisu",
        "description": (
            "Authentic Italian tiramisu with mascarpone, espresso-soaked savoiardi and "
            "Marsala wine. Dusted with cocoa."
        ),
        "price": 6.80,
        "photo_url": "assets/photos/23_tiramisu.jpg",
    },
    {
        "category": "Pastries & Desserts",
        "name": "Blueberry Muffin",
        "description": (
            "Moist sour-cream muffin packed with wild blueberries and finished with "
            "a crunchy demerara sugar top."
        ),
        "price": 4.00,
        "photo_url": "assets/photos/24_blueberry_muffin.jpg",
    },
    {
        "category": "Pastries & Desserts",
        "name": "Double Chocolate Brownie",
        "description": (
            "Fudgy 70% dark chocolate brownie with walnuts and a glossy ganache top. "
            "Naturally gluten-free."
        ),
        "price": 4.50,
        "photo_url": "assets/photos/25_brownie.jpg",
    },
    # ── Single Origin Beans ──────────────────────────────────────────────
    {
        "category": "Single Origin Beans",
        "name": "Ethiopian Yirgacheffe (250 g)",
        "description": (
            "Bright and floral with notes of jasmine, bergamot and ripe peach. "
            "Washed process, light roast. Perfect for pour-over."
        ),
        "price": 18.50,
        "photo_url": "assets/photos/26_ethiopian_yirgacheffe.jpg",
    },
    {
        "category": "Single Origin Beans",
        "name": "Colombian Huila Supremo (250 g)",
        "description": (
            "Balanced cup with caramel sweetness, milk chocolate and a soft red apple finish. "
            "Medium roast — works equally well as filter or espresso."
        ),
        "price": 16.00,
        "photo_url": "assets/photos/27_colombian_huila.jpg",
    },
    {
        "category": "Single Origin Beans",
        "name": "Kenya AA Nyeri (250 g)",
        "description": (
            "Juicy and complex: blackcurrant, tomato vine, brown sugar. "
            "An SCA-87 cupping score from a small Nyeri cooperative."
        ),
        "price": 22.00,
        "photo_url": "assets/photos/28_kenya_aa.jpg",
    },
    {
        "category": "Single Origin Beans",
        "name": "Guatemala Antigua (250 g)",
        "description": (
            "Volcanic-soil grown beans with cocoa, pipe tobacco and brown sugar notes. "
            "Medium-dark roast, full body."
        ),
        "price": 17.50,
        "photo_url": "assets/photos/29_guatemala_antigua.jpg",
    },
    {
        "category": "Single Origin Beans",
        "name": "Brazil Cerrado (250 g)",
        "description": (
            "Low-acidity, smooth and nutty with notes of milk chocolate and almond. "
            "An everyday favourite, pulped natural process."
        ),
        "price": 14.00,
        "photo_url": "assets/photos/30_brazil_cerrado.jpg",
    },
    # ── Espresso Blends ──────────────────────────────────────────────────
    {
        "category": "Espresso Blends",
        "name": "House Espresso Blend (1 kg)",
        "description": (
            "Our signature 70/30 Brazil-Ethiopia blend. Hazelnut, dark chocolate, "
            "creamy body. Designed for milk drinks but shines as a straight shot."
        ),
        "price": 38.00,
        "photo_url": "assets/photos/31_house_blend.jpg",
    },
    {
        "category": "Espresso Blends",
        "name": "Dark Roast Italian Blend (500 g)",
        "description": (
            "Old-school Italian profile — bold, smoky, with bittersweet chocolate. "
            "Cuts cleanly through milk for unforgettable cappuccinos."
        ),
        "price": 22.00,
        "photo_url": "assets/photos/32_dark_roast.jpg",
    },
    {
        "category": "Espresso Blends",
        "name": "Decaf Swiss Water Blend (500 g)",
        "description": (
            "99.9% caffeine-free using the chemical-free Swiss Water process. "
            "Notes of cocoa, almond and dried fig. Tastes like real coffee — not a compromise."
        ),
        "price": 21.00,
        "photo_url": "assets/photos/33_decaf.jpg",
    },
    # ── Brewing Equipment ────────────────────────────────────────────────
    {
        "category": "Brewing Equipment",
        "name": "Hario V60-02 Ceramic Dripper",
        "description": (
            "The pour-over classic. 60-degree cone, spiral ribs and a single large hole "
            "for full control over flow rate. Includes 40 paper filters."
        ),
        "price": 28.90,
        "photo_url": "assets/photos/34_hario_v60.jpg",
    },
    {
        "category": "Brewing Equipment",
        "name": "AeroPress Original",
        "description": (
            "Brews a clean, full-flavoured cup in under a minute. "
            "Travel-friendly, near-indestructible. Includes 350 micro-filters."
        ),
        "price": 39.95,
        "photo_url": "assets/photos/35_aeropress.jpg",
    },
    {
        "category": "Brewing Equipment",
        "name": "Chemex 6-Cup Brewer",
        "description": (
            "Iconic hourglass borosilicate carafe with wooden collar and leather tie. "
            "Produces an exceptionally clean, tea-like cup."
        ),
        "price": 49.00,
        "photo_url": "assets/photos/36_chemex.jpg",
    },
    {
        "category": "Brewing Equipment",
        "name": "French Press 1 L",
        "description": (
            "Classic borosilicate French press with stainless mesh filter. "
            "Full-bodied, oils and all — the easiest way to brew at home."
        ),
        "price": 32.00,
        "photo_url": "assets/photos/37_french_press.jpg",
    },
    # ── Accessories ──────────────────────────────────────────────────────
    {
        "category": "Accessories",
        "name": "Acaia Pearl Brewing Scale",
        "description": (
            "0.1 g resolution, 20 ms response time, built-in brewing timer and "
            "Bluetooth app. The competition standard for serious home baristas."
        ),
        "price": 165.00,
        "photo_url": "assets/photos/38_coffee_scale.jpg",
    },
    {
        "category": "Accessories",
        "name": "Ceramic Mug Set (2 × 250 ml)",
        "description": (
            "Hand-thrown stoneware mugs in matte navy. Comfortable handle, "
            "thick walls keep coffee hot. Microwave and dishwasher safe."
        ),
        "price": 24.00,
        "photo_url": "assets/photos/39_mug_set.jpg",
    },
    {
        "category": "Accessories",
        "name": "Stainless Travel Thermos (500 ml)",
        "description": (
            "Double-wall vacuum insulated tumbler — keeps coffee hot for 12 h "
            "or cold brew icy for 24 h. Leak-proof lid."
        ),
        "price": 32.00,
        "photo_url": "assets/photos/40_travel_thermos.jpg",
    },
]


async def seed_if_empty(db: Database) -> int:
    """Populate or refresh the catalog so it always matches ``PRODUCTS``.

    Behaviour:
    - **Empty DB** → insert all ``PRODUCTS`` and ``CATEGORIES``.
    - **DB matches** the current ``PRODUCTS`` (same count + same first-row
      photo path) → no-op.
    - **DB drifted** from the seed (e.g. you renamed photos / added items in
      ``seed_data.py`` after a previous run) → wipe ``products`` and
      ``categories`` and re-insert everything. ``order_items`` keeps a
      denormalised name/price so historical orders survive untouched;
      ``cart_items`` are cleaned via the FK ON DELETE CASCADE.

    Returns the number of products inserted (0 when no work was needed).
    """
    actual_count = await db.count_products()
    expected_count = len(PRODUCTS)

    if actual_count == expected_count:
        # Cheap drift check: the first product's photo_url must match the seed.
        first = await db.get_product(1, include_out_of_stock=True)
        if first and first.photo_url == PRODUCTS[0]["photo_url"]:
            return 0  # already up to date

    if actual_count > 0:
        # Drift detected — wipe and rebuild the catalog.
        # cart_items vanish via FK CASCADE; orders/order_items keep their
        # denormalised name/price snapshots.
        await db.conn.execute("DELETE FROM products")
        await db.conn.execute("DELETE FROM categories")
        # Reset AUTOINCREMENT counters so new ids start from 1 again.
        # This keeps callback_data values stable across re-seeds.
        await db.conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('products', 'categories')"
        )
        await db.conn.commit()

    category_ids: dict[str, int] = {}
    for name, emoji in CATEGORIES.items():
        category_ids[name] = await db.add_category(name, emoji)

    inserted = 0
    for product in PRODUCTS:
        await db.add_product(
            category_id=category_ids[product["category"]],
            name=product["name"],
            description=product["description"],
            price=product["price"],
            photo_url=product["photo_url"],
        )
        inserted += 1
    return inserted
