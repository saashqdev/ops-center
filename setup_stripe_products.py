#!/usr/bin/env python3
"""
Setup Stripe Products for Credit Packages

Creates Stripe products and prices for each credit package in the database.
Updates the credit_packages table with the Stripe IDs.

Usage: python setup_stripe_products.py
"""

import os
import asyncio
import asyncpg
import stripe
from decimal import Decimal

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

async def setup_stripe_products():
    """Create Stripe products for all credit packages"""
    
    # Connect to database
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "unicorn"),
        password=os.getenv("POSTGRES_PASSWORD", "change-me"),
        database=os.getenv("POSTGRES_DB", "unicorn_db")
    )
    
    try:
        # Get all credit packages
        packages = await conn.fetch(
            "SELECT * FROM credit_packages WHERE is_active = TRUE ORDER BY credits"
        )
        
        print(f"Found {len(packages)} credit packages to process\n")
        
        for pkg in packages:
            print(f"Processing: {pkg['package_name']}")
            print(f"  Code: {pkg['package_code']}")
            print(f"  Credits: {pkg['credits']:,}")
            print(f"  Price: ${pkg['price_usd']}")
            
            # Check if already has Stripe IDs
            if pkg['stripe_product_id'] and pkg['stripe_price_id']:
                print(f"  ✓ Already has Stripe IDs - skipping")
                print()
                continue
            
            # Create Stripe product
            try:
                product = stripe.Product.create(
                    name=pkg['package_name'],
                    description=pkg['description'] or f"{pkg['credits']:,} AI credits",
                    metadata={
                        'package_code': pkg['package_code'],
                        'credits': str(pkg['credits']),
                        'discount_percentage': str(pkg['discount_percentage'])
                    }
                )
                print(f"  ✓ Created Stripe product: {product.id}")
                
                # Create Stripe price (one-time payment)
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(float(pkg['price_usd']) * 100),  # Convert to cents
                    currency='usd',
                    metadata={
                        'package_code': pkg['package_code'],
                        'credits': str(pkg['credits'])
                    }
                )
                print(f"  ✓ Created Stripe price: {price.id}")
                
                # Update database with Stripe IDs
                await conn.execute(
                    """
                    UPDATE credit_packages
                    SET stripe_product_id = $1, stripe_price_id = $2
                    WHERE package_code = $3
                    """,
                    product.id,
                    price.id,
                    pkg['package_code']
                )
                print(f"  ✓ Updated database")
                print()
                
            except stripe.error.StripeError as e:
                print(f"  ✗ Stripe error: {e}")
                print()
                continue
        
        print("\n✅ Stripe setup complete!")
        
        # Show summary
        updated = await conn.fetch(
            "SELECT package_name, stripe_product_id, stripe_price_id FROM credit_packages WHERE is_active = TRUE"
        )
        
        print("\nCurrent Stripe configuration:")
        print("-" * 80)
        for pkg in updated:
            status = "✓" if pkg['stripe_product_id'] and pkg['stripe_price_id'] else "✗"
            print(f"{status} {pkg['package_name']:<20} Product: {pkg['stripe_product_id'] or 'None':<25} Price: {pkg['stripe_price_id'] or 'None'}")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(setup_stripe_products())
