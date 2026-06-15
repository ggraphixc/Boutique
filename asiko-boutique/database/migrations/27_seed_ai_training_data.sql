-- Migration 27: Seed AI Stylist training data with default brand knowledge

INSERT INTO ai_training_data (category, question, answer, is_active, sort_order) VALUES
-- Brand knowledge
('brand', 'What is ASIKO?', 'ASIKO Boutique is a Nigerian fashion brand offering authentic, curated styles with transparent pricing. Every piece is crafted with verified provenance and fair-trade standards. We specialize in contemporary Nigerian fashion — from everyday wear to statement pieces.', TRUE, 1),
('brand', 'What does ASIKO mean?', 'ASIKO means "time" or "era" in Yoruba. It represents timeless fashion that transcends trends — pieces you''ll love for years, not just seasons.', TRUE, 2),
('brand', 'Where is ASIKO located?', 'ASIKO Boutique is based in Lagos, Nigeria. We ship nationwide across all 36 states and the FCT, plus international shipping to select countries.', TRUE, 3),
('brand', 'What makes ASIKO different?', 'We combine verified provenance, transparent pricing (no "DM for price"), and fair-trade standards. Every product shows its real price upfront. We also offer an AI Stylist to help you find the perfect outfit.', TRUE, 4),

-- FAQ
('faq', 'Do you have physical stores?', 'Currently ASIKO operates online only at asikoboutique.com. This means lower overhead and better prices for you. We''re working on pop-up events in Lagos — follow us on social media for updates.', TRUE, 10),
('faq', 'What sizes do you carry?', 'We carry sizes XS through XXL for most items. Each product page has a detailed size guide with measurements. Our AI Stylist can also recommend the best size for your body type.', TRUE, 11),
('faq', 'How do I track my order?', 'Once your order ships, you''ll receive an email with a tracking number. You can also check your order status anytime in the My Orders section of your account.', TRUE, 12),
('faq', 'Do you offer alterations?', 'We don''t offer in-house alterations yet, but many of our pieces are designed to be easily tailored by a local seamstress. Check the product description for fit notes.', TRUE, 13),
('faq', 'Can I return or exchange an item?', 'Yes! We accept returns and exchanges within 7 days of delivery. Items must be unworn with tags attached. Contact us at support@asikoboutique.com to start a return.', TRUE, 14),

-- Style rules
('style', 'What styles does ASIKO specialize in?', 'ASIKO offers a mix of contemporary Nigerian fashion and classic pieces. Our collections include: Ankara prints, Aso-Oke, Adire (tie-dye), solid-color modern pieces, and fusion styles that blend Nigerian heritage with global trends. We cater to both casual everyday wear and special occasion pieces.', TRUE, 20),
('style', 'How do I style for Nigerian weather?', 'For Nigeria''s tropical climate: lightweight cotton and linen for the dry season (Nov-Mar), breathable fabrics for the rainy season (Apr-Oct), and layerable pieces for harmattan. Our AI Stylist can suggest outfits based on your location and the current season.', TRUE, 21),
('style', 'What are popular outfit combinations?', 'Popular Nigerian outfit pairings: Ankara top + solid skirt/trousers, Adire dress + leather accessories, Aso-Oke wrapper + modern blouse for events, solid-colored agbada for men, and mix-and-match separates for everyday wear.', TRUE, 22),
('style', 'How should I accessorize Nigerian fashion?', 'Less is more with bold prints — pair Ankara pieces with solid accessories. For solid outfits, add statement jewelry or a colorful gele. Leather bags and shoes work with everything. Gold-toned jewelry complements warm-toned fabrics.', TRUE, 23),

-- Voice
('voice', 'How should the AI Stylist communicate?', 'The AI Stylist should be warm, friendly, and knowledgeable — like a trusted fashion-savvy friend. Use Nigerian English naturally (no heavy slang). Be enthusiastic about fashion but practical in advice. Always reference specific products from the catalog when relevant. Use ₦ for prices.', TRUE, 30),
('voice', 'What tone should the AI Stylist use?', 'Conversational, helpful, and confident. Not overly formal or robotic. Think of a knowledgeable boutique owner who genuinely cares about helping customers look their best. It''s okay to be playful and use fashion emojis occasionally.', TRUE, 31);

-- Update timestamp for any existing rows that match
UPDATE ai_training_data SET updated_at = NOW() WHERE category IN ('brand', 'faq', 'style', 'voice');
