#!/usr/bin/env python3
"""
Script to create a new tenant and its admin user.

This script:
1. Creates a new user (or uses an existing one)
2. Creates a tenant and associates the user as ADMIN
3. Generates a one-time use token (no expiration) to set the password
4. The token can only be used once

Usage:
  python scripts/create_tenant.py --email admin@example.com [--tenant-id UUID]

The script will print the link to set the password.
"""

import asyncio
import secrets
import sys
from pathlib import Path
from uuid import UUID, uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.use_cases.auth import bootstrap_tenant
from src.config.settings import get_settings
from src.domain.models.one_time_token import OneTimeToken
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.session import (
    SQLAlchemyUnitOfWork,
    create_engine,
    create_session_factory,
)
from src.infrastructure.email.renderer.engine import EmailTemplateRenderer


async def create_tenant_with_token(email: str, tenant_id: UUID | None = None):
    """
    Create a new tenant with its admin.
    If the user doesn't exist, creates it with a temporary password and generates a one-time token.
    If the user exists, just associates it to the tenant.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    password_hasher = PasswordHasher()

    tenant_uuid = tenant_id or uuid4()
    created_user = False

    try:
        # Check if the user already exists
        uow = SQLAlchemyUnitOfWork(session_factory)
        async with uow:
            existing_user = await uow.users.get_by_email(email)

            if existing_user:
                print(f"ℹ️  User {email} already exists (ID: {existing_user.id})")
                user_id = existing_user.id
            else:
                created_user = True
                # User doesn't exist, will be created in bootstrap_tenant with temp password
                print(f"✨ Creating new user: {email}")
                # Use a temporary password that will be replaced
                temp_password = secrets.token_urlsafe(32)

        # Create the tenant (and user if it doesn't exist)
        uow = SQLAlchemyUnitOfWork(session_factory)
        async with uow:
            result = await bootstrap_tenant.execute(
                uow=uow,
                payload=bootstrap_tenant.RegisterTenantInput(
                    email=email,
                    password=temp_password if created_user else "unused",
                    tenant_id=tenant_uuid,
                ),
                password_hasher=password_hasher,
            )

        user_id = result.user_id

        print("\n✅ Tenant created successfully!")
        print(f"   Tenant ID: {result.tenant_id}")
        print(f"   User ID: {result.user_id}")
        print(f"   Email: {result.email}")

        # If we created a new user, generate one-time token
        if created_user:
            uow = SQLAlchemyUnitOfWork(session_factory)

            # Generate secure one-time token
            token_value = secrets.token_urlsafe(32)
            one_time_token = OneTimeToken.create(
                token=token_value,
                user_id=user_id,
                purpose="set_password",
                extra_data={"tenant_id": str(tenant_uuid), "role": "ADMIN", "created_via": "cli"},
            )

            async with uow:
                await uow.one_time_tokens.add(one_time_token)
                await uow.commit()

            print("\n🔑 One-time token generated")
            print(f"   Token ID: {one_time_token.id}")

            # Build link for setting password
            base_url = settings.email_reset_url_base or "https://app.lechefacil.com"
            set_password_link = f"{base_url.rstrip('/')}/set-password?token={token_value}"

            print("\n📧 Link to set password:")
            print(f"   {set_password_link}")
            print("\n   ⚠️  This link:")
            print("   - Is for one-time use only")
            print("   - Does not expire")
            print("   - Will be invalidated after use")

            # Send email to the user
            try:
                # Initialize email service based on settings
                provider = settings.email_provider.lower()
                email_service = None

                if provider == "ses":
                    try:
                        from src.infrastructure.email.providers.ses_provider import SESEmailService

                        email_service = SESEmailService()
                        print("\n📧 Using SES email provider")
                    except Exception as exc:
                        print(f"\n⚠️  Failed to init SES provider: {exc}")
                elif provider == "unione":
                    try:
                        from src.infrastructure.email.providers.unione_provider import (
                            UniOneEmailService,
                        )

                        if settings.unione_api_key:
                            email_service = UniOneEmailService(
                                api_key=settings.unione_api_key.get_secret_value(),
                                api_url=settings.unione_api_url,
                            )
                            print("\n📧 Using UniOne email provider")
                        else:
                            print("\n⚠️  UNIONE_API_KEY not configured")
                    except Exception as exc:
                        print(f"\n⚠️  Failed to init UniOne provider: {exc}")

                # Fallback to logging provider
                if email_service is None:
                    from src.infrastructure.email.providers.logging_provider import (
                        LoggingEmailService,
                    )

                    email_service = LoggingEmailService()
                    print("\n📧 Using Logging email provider (no actual email sent)")

                # Render and send email
                renderer = EmailTemplateRenderer.create_default()

                # Render invitation email (reusing membership_invite template for tenant admin)
                rendered = renderer.render(
                    template_key="membership_invite",
                    settings=settings,
                    context={
                        "user_email": email,
                        "tenant_name": "LecheFácil",  # Could be parameterized
                        "role": "ADMIN",
                        "is_new_user": True,
                        "set_password_link": set_password_link,
                        "login_link": base_url.rstrip("/") + "/login",
                    },
                    locale="es",
                )

                # Update the rendered message with recipients and sender info
                rendered.to = [email]
                rendered.from_email = settings.email_from_address
                rendered.from_name = settings.email_from_name

                await email_service.send(rendered)
                print(f"\n✅ Email sent successfully to {email}")

            except Exception as email_exc:
                print(f"\n⚠️  Failed to send email: {email_exc}")
                print("   Please send the link manually to the user.")
        else:
            print("\n✅ Existing user associated to tenant as ADMIN")
            print("   User can log in with their current password")

    except Exception as exc:
        print(f"\n❌ Error creating tenant: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a new tenant with admin user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create tenant with new user
  python scripts/create_tenant.py --email admin@example.com

  # Create tenant with specific ID
  python scripts/create_tenant.py --email admin@example.com 
  --tenant-id 12345678-1234-5678-1234-567812345678

  # Associate existing user to new tenant
  python scripts/create_tenant.py --email existing@user.com
        """,
    )
    parser.add_argument("--email", required=True, help="Email of the tenant admin")
    parser.add_argument("--tenant-id", help="Tenant ID (optional, auto-generated)")

    args = parser.parse_args()

    tenant_uuid = None
    if args.tenant_id:
        try:
            tenant_uuid = UUID(args.tenant_id)
        except ValueError:
            print(f"❌ Error: '{args.tenant_id}' is not a valid UUID")
            sys.exit(1)

    print("=" * 60)
    print("🚀 Tenant Creator - LecheFacil")
    print("=" * 60)

    asyncio.run(create_tenant_with_token(args.email, tenant_uuid))

    print("\n" + "=" * 60)
    print("✨ Process completed")
    print("=" * 60)
