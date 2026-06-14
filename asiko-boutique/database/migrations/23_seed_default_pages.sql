-- Migration 23: Seed default custom pages
-- About Us, Size Guide, Shipping & Returns, Contact

INSERT INTO custom_pages (title, slug, page_type, body_html, excerpt, meta_description, show_in_nav, show_in_footer, is_live, sort_order) VALUES

('About Us', 'about-us', 'content',
'<h2>Welcome to ASIKO Boutique</h2>
<p>ASIKO is more than a fashion brand — it''s a celebration of African elegance, craftsmanship, and modern style. Founded in 2024, we bring you carefully curated pieces that blend traditional Nigerian aesthetics with contemporary fashion.</p>

<h3>Our Story</h3>
<p>What started as a passion project has grown into a beloved boutique trusted by fashion-forward women across Nigeria. Every piece in our collection is selected with care, ensuring quality fabrics, impeccable tailoring, and timeless designs.</p>

<h3>Our Mission</h3>
<p>To empower every woman to express her unique style through beautifully crafted, affordable fashion that celebrates African heritage.</p>

<h3>Why Shop With Us?</h3>
<ul>
<li><strong>Quality Fabrics:</strong> We source only the finest materials — from premium lace to genuine leather.</li>
<li><strong>Perfect Fit:</strong> Our AI-powered virtual try-on helps you find your perfect size before you buy.</li>
<li><strong>Fast Delivery:</strong> We deliver across Nigeria within 3-5 business days.</li>
<li><strong>Secure Payments:</strong> Pay with OPay — trusted by millions of Nigerians.</li>
</ul>',
'Learn about ASIKO Boutique — our story, mission, and commitment to quality African fashion.',
'ASIKO Boutique - Premium Nigerian fashion. Shop curated dresses, shirts, and accessories with virtual try-on and fast delivery.',
FALSE, TRUE, TRUE, 1),

('Size Guide', 'size-guide', 'content',
'<h2>Size Guide</h2>
<p>Finding the right fit is everything. Use our comprehensive size guide to shop with confidence.</p>

<h3>Women''s Clothing</h3>
<table class="w-full border-collapse">
<thead><tr><th class="border border-gray-200 p-2 text-left">Size</th><th class="border border-gray-200 p-2 text-left">Bust (inches)</th><th class="border border-gray-200 p-2 text-left">Waist (inches)</th><th class="border border-gray-200 p-2 text-left">Hips (inches)</th></tr></thead>
<tbody>
<tr><td class="border border-gray-200 p-2">XS (6)</td><td class="border border-gray-200 p-2">32-33</td><td class="border border-gray-200 p-2">24-25</td><td class="border border-gray-200 p-2">34-35</td></tr>
<tr><td class="border border-gray-200 p-2">S (8)</td><td class="border border-gray-200 p-2">34-35</td><td class="border border-gray-200 p-2">26-27</td><td class="border border-gray-200 p-2">36-37</td></tr>
<tr><td class="border border-gray-200 p-2">M (10)</td><td class="border border-gray-200 p-2">36-37</td><td class="border border-gray-200 p-2">28-29</td><td class="border border-gray-200 p-2">38-39</td></tr>
<tr><td class="border border-gray-200 p-2">L (12)</td><td class="border border-gray-200 p-2">38-39</td><td class="border border-gray-200 p-2">30-31</td><td class="border border-gray-200 p-2">40-41</td></tr>
<tr><td class="border border-gray-200 p-2">XL (14)</td><td class="border border-gray-200 p-2">40-41</td><td class="border border-gray-200 p-2">32-33</td><td class="border border-gray-200 p-2">42-43</td></tr>
<tr><td class="border border-gray-200 p-2">XXL (16)</td><td class="border border-gray-200 p-2">42-43</td><td class="border border-gray-200 p-2">34-35</td><td class="border border-gray-200 p-2">44-45</td></tr>
</tbody>
</table>

<h3>How to Measure</h3>
<p><strong>Bust:</strong> Measure around the fullest part of your chest.</p>
<p><strong>Waist:</strong> Measure around the narrowest part of your natural waist.</p>
<p><strong>Hips:</strong> Measure around the fullest part of your hips and bum.</p>

<h3>Between Sizes?</h3>
<p>If you''re between sizes, we recommend sizing up for a more comfortable fit. Our AI Stylist can also help you find your perfect size based on your body measurements.</p>

<h3>Need Help?</h3>
<p>Chat with our <a href="/stylist">AI Stylist</a> for personalized size recommendations.</p>',
'Find your perfect fit with ASIKO''s comprehensive size guide for women''s clothing.',
'ASIKO Boutique size guide — find your perfect fit with our detailed measurements chart.',
FALSE, TRUE, TRUE, 2),

('Shipping & Returns', 'shipping-returns', 'content',
'<h2>Shipping & Returns</h2>

<h3>Delivery</h3>
<p>We deliver across Nigeria! Here''s what to expect:</p>
<ul>
<li><strong>Lagos:</strong> 1-2 business days</li>
<li><strong>Other States:</strong> 3-5 business days</li>
<li><strong>Remote Areas:</strong> 5-7 business days</li>
</ul>

<h3>Shipping Rates</h3>
<table class="w-full border-collapse">
<thead><tr><th class="border border-gray-200 p-2 text-left">Location</th><th class="border border-gray-200 p-2 text-left">Standard</th><th class="border border-gray-200 p-2 text-left">Express</th></tr></thead>
<tbody>
<tr><td class="border border-gray-200 p-2">Lagos</td><td class="border border-gray-200 p-2">&#8358;1,500</td><td class="border border-gray-200 p-2">&#8358;3,000</td></tr>
<tr><td class="border border-gray-200 p-2">South-West</td><td class="border border-gray-200 p-2">&#8358;2,000</td><td class="border border-gray-200 p-2">&#8358;4,000</td></tr>
<tr><td class="border border-gray-200 p-2">Other States</td><td class="border border-gray-200 p-2">&#8358;2,500</td><td class="border border-gray-200 p-2">&#8358;5,000</td></tr>
</tbody>
</table>

<p><strong>Free shipping</strong> on orders over &#8358;50,000!</p>

<h3>Payment</h3>
<p>We accept payments via <strong>OPay</strong> — fast, secure, and trusted by millions of Nigerians.</p>

<h3>Returns & Exchanges</h3>
<p>Your satisfaction matters. If you''re not happy with your purchase:</p>
<ul>
<li>Return within <strong>7 days</strong> of delivery</li>
<li>Item must be unworn with tags attached</li>
<li>Refund processed within 5-7 business days</li>
<li>Exchange available for different size or color</li>
</ul>

<h3>How to Return</h3>
<ol>
<li>Contact us via chat or email with your order number</li>
<li>We''ll arrange a pickup or provide a return address</li>
<li>Once we receive and inspect the item, your refund is processed</li>
</ol>

<p><strong>Non-returnable items:</strong> Accessories, swimwear, and items marked as "Final Sale".</p>',
'Learn about ASIKO Boutique shipping rates, delivery times, and return policy.',
'ASIKO Boutique shipping and returns — fast delivery across Nigeria, easy returns within 7 days.',
FALSE, TRUE, TRUE, 3),

('Contact Us', 'contact-us', 'content',
'<h2>Contact Us</h2>
<p>We''d love to hear from you! Whether you have a question about an order, need sizing advice, or want to collaborate — reach out anytime.</p>

<h3>Get in Touch</h3>
<table class="w-full border-collapse">
<tbody>
<tr><td class="border border-gray-200 p-3 font-semibold">Email</td><td class="border border-gray-200 p-2">hello@asikoboutique.ng</td></tr>
<tr><td class="border border-gray-200 p-3 font-semibold">Phone</td><td class="border border-gray-200 p-2">+234 800 ASIKO (274 566)</td></tr>
<tr><td class="border border-gray-200 p-3 font-semibold">WhatsApp</td><td class="border border-gray-200 p-2">+234 801 234 5678</td></tr>
<tr><td class="border border-gray-200 p-3 font-semibold">Instagram</td><td class="border border-gray-200 p-2">@asikoboutique</td></tr>
<tr><td class="border border-gray-200 p-3 font-semibold">Address</td><td class="border border-gray-200 p-2">12 Admiralty Way, Lekki Phase 1, Lagos, Nigeria</td></tr>
</tbody>
</table>

<h3>Business Hours</h3>
<p>Monday - Friday: 9:00 AM - 6:00 PM</p>
<p>Saturday: 10:00 AM - 4:00 PM</p>
<p>Sunday: Closed</p>

<h3>Quick Help</h3>
<ul>
<li><strong>Order issues:</strong> Chat with us or WhatsApp your order number</li>
<li><strong>Sizing help:</strong> Try our <a href="/stylist">AI Stylist</a> for instant recommendations</li>
<li><strong>Returns:</strong> See our <a href="/page/shipping-returns">Shipping & Returns</a> page</li>
<li><strong>Wholesale inquiries:</strong> Email wholesale@asikoboutique.ng</li>
</ul>',
'Get in touch with ASIKO Boutique — email, phone, WhatsApp, and store location.',
'Contact ASIKO Boutique — reach us via email, phone, WhatsApp. Visit our store in Lekki, Lagos.',
FALSE, TRUE, TRUE, 4)

ON CONFLICT (slug) DO NOTHING;
