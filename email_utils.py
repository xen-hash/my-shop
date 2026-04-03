"""
email_utils.py – GadgetHub PH
================================
Handles all transactional emails via Flask-Mail.
"""

from flask import current_app
from flask_mail import Mail, Message
from threading import Thread

mail = Mail()


def _send_async(app, msg):
    """Send email in a background thread so it doesn't block the request."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"[GadgetHub Mail] Failed to send email: {e}")


def send_email(subject, recipients, html_body, text_body=None):
    """Generic email sender. Runs in a background thread."""
    app = current_app._get_current_object()
    msg = Message(
        subject    = subject,
        recipients = recipients if isinstance(recipients, list) else [recipients],
        html       = html_body,
        body       = text_body or "Please view this email in an HTML-compatible client.",
        sender     = app.config.get("MAIL_DEFAULT_SENDER", "GadgetHub PH <noreply@gadgethub.ph>")
    )
    Thread(target=_send_async, args=(app, msg)).start()


# ─────────────────────────────────────────────────────────────
# ORDER CONFIRMATION EMAIL
# ─────────────────────────────────────────────────────────────

def send_order_confirmation(user, order, order_items):
    """
    Send a beautiful HTML order confirmation email.

    Args:
        user        – User model instance
        order       – Order model instance
        order_items – list of OrderItem model instances (with .product attached)
    """

    # Build the items table rows
    items_rows = ""
    for item in order_items:
        subtotal = item.quantity * float(item.unit_price) / 100
        items_rows += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #2d1f44;">
            <div style="font-weight:600;color:#eedbff;font-size:14px;">{item.product.name}</div>
            <div style="color:#8888aa;font-size:12px;margin-top:2px;">{item.product.category.capitalize()}</div>
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid #2d1f44;text-align:center;
                     color:#c9c4d8;font-size:14px;">×{item.quantity}</td>
          <td style="padding:12px 16px;border-bottom:1px solid #2d1f44;text-align:right;
                     color:#cabeff;font-weight:700;font-size:14px;">
            ₱{subtotal:,.2f}
          </td>
        </tr>
        """

    total = float(order.total_price) / 100
    order_num = f"GH-{order.id:04d}"
    placed_at = order.created_at.strftime("%B %d, %Y at %I:%M %p")

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Order Confirmed – GadgetHub PH</title>
</head>
<body style="margin:0;padding:0;background-color:#0d0820;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0820;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:#150726;border-radius:20px;
                      overflow:hidden;border:1px solid #2d1f44;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a0c2b 0%,#271938 100%);
                       padding:40px 40px 32px;text-align:center;
                       border-bottom:1px solid #2d1f44;">
              <!-- Logo / Brand -->
              <div style="font-size:28px;font-weight:800;letter-spacing:-0.5px;margin-bottom:4px;">
                <span style="color:#cabeff;">Gadget</span><span style="color:#947dff;">Hub</span>
                <span style="color:#cabeff;"> PH</span>
              </div>
              <div style="color:#8888aa;font-size:12px;letter-spacing:2px;text-transform:uppercase;
                          margin-bottom:28px;">🇵🇭 Tech for Every Filipino</div>

              <!-- Checkmark -->
              <div style="width:72px;height:72px;border-radius:50%;background:rgba(0,212,170,0.12);
                          border:2px solid rgba(0,212,170,0.4);margin:0 auto 16px;
                          display:flex;align-items:center;justify-content:center;
                          line-height:72px;font-size:32px;">✅</div>

              <h1 style="margin:0 0 8px;font-size:26px;font-weight:800;color:#fff;letter-spacing:-0.5px;">
                Order Confirmed!
              </h1>
              <p style="margin:0;color:#c9c4d8;font-size:15px;line-height:1.5;">
                Thanks, <strong style="color:#cabeff;">{user.name.split()[0]}</strong>!
                Your order is being prepared. 🚀
              </p>
            </td>
          </tr>

          <!-- Order Meta -->
          <tr>
            <td style="padding:28px 40px;border-bottom:1px solid #2d1f44;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="width:50%;padding-right:8px;">
                    <div style="background:#1e1133;border-radius:12px;padding:16px;">
                      <div style="color:#8888aa;font-size:11px;text-transform:uppercase;
                                  letter-spacing:1.5px;margin-bottom:6px;">Order Number</div>
                      <div style="color:#cabeff;font-size:18px;font-weight:800;">#{order_num}</div>
                    </div>
                  </td>
                  <td style="width:50%;padding-left:8px;">
                    <div style="background:#1e1133;border-radius:12px;padding:16px;">
                      <div style="color:#8888aa;font-size:11px;text-transform:uppercase;
                                  letter-spacing:1.5px;margin-bottom:6px;">Date Placed</div>
                      <div style="color:#eedbff;font-size:13px;font-weight:600;">{placed_at}</div>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Shipping Address -->
          <tr>
            <td style="padding:20px 40px;border-bottom:1px solid #2d1f44;">
              <div style="color:#8888aa;font-size:11px;text-transform:uppercase;
                          letter-spacing:1.5px;margin-bottom:10px;">📦 Shipping To</div>
              <div style="color:#c9c4d8;font-size:14px;line-height:1.6;
                          background:#1e1133;border-radius:10px;padding:14px 16px;">
                {order.shipping_address}
              </div>
            </td>
          </tr>

          <!-- Items -->
          <tr>
            <td style="padding:20px 40px 0;">
              <div style="color:#8888aa;font-size:11px;text-transform:uppercase;
                          letter-spacing:1.5px;margin-bottom:10px;">🛒 Items Ordered</div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#1e1133;border-radius:12px;overflow:hidden;">
                <thead>
                  <tr style="background:#271938;">
                    <th style="padding:10px 16px;text-align:left;color:#8888aa;
                               font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                      Product
                    </th>
                    <th style="padding:10px 16px;text-align:center;color:#8888aa;
                               font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                      Qty
                    </th>
                    <th style="padding:10px 16px;text-align:right;color:#8888aa;
                               font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;">
                      Price
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items_rows}
                </tbody>
              </table>
            </td>
          </tr>

          <!-- Total -->
          <tr>
            <td style="padding:0 40px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#271938;border-radius:12px;padding:16px;">
                <tr>
                  <td style="padding:6px 16px;color:#c9c4d8;font-size:14px;">Subtotal</td>
                  <td style="padding:6px 16px;text-align:right;color:#eedbff;font-size:14px;">
                    ₱{total:,.2f}
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 16px;color:#c9c4d8;font-size:14px;">Shipping</td>
                  <td style="padding:6px 16px;text-align:right;color:#00d4aa;
                             font-size:14px;font-weight:700;">FREE 🎉</td>
                </tr>
                <tr style="border-top:1px solid #3d2e4f;">
                  <td style="padding:12px 16px;color:#fff;font-size:16px;font-weight:800;">
                    Total
                  </td>
                  <td style="padding:12px 16px;text-align:right;color:#cabeff;
                             font-size:22px;font-weight:800;">
                    ₱{total:,.2f}
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA Button -->
          <tr>
            <td style="padding:0 40px 32px;text-align:center;">
              <a href="https://gadgethub.ph/orders/{order.id}"
                 style="display:inline-block;padding:14px 36px;border-radius:12px;
                        background:linear-gradient(135deg,#cabeff,#947dff);
                        color:#2b0088;font-weight:800;font-size:15px;
                        text-decoration:none;letter-spacing:-0.3px;">
                Track My Order →
              </a>
            </td>
          </tr>

          <!-- Info Banner -->
          <tr>
            <td style="padding:0 40px 28px;">
              <div style="background:rgba(148,125,255,0.08);border:1px solid rgba(148,125,255,0.2);
                          border-radius:12px;padding:16px 20px;text-align:center;">
                <p style="margin:0;color:#c9c4d8;font-size:13px;line-height:1.6;">
                  📬 <strong style="color:#cabeff;">Free nationwide delivery</strong> within
                  3–5 business days.<br>
                  Questions? Reply to this email or message us on Facebook.
                </p>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#0d0820;padding:24px 40px;text-align:center;
                       border-top:1px solid #2d1f44;">
              <p style="margin:0 0 8px;color:#8888aa;font-size:12px;">
                © 2025 GadgetHub PH · Made with ❤️ for Filipinos
              </p>
              <p style="margin:0;color:#3d2e4f;font-size:11px;">
                You received this email because you placed an order on GadgetHub PH.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""

    plain = f"""
GadgetHub PH – Order Confirmed!

Hi {user.name},

Your order #{order_num} has been confirmed and is being prepared.

Order Total: ₱{total:,.2f}
Shipping: FREE
Placed: {placed_at}

Shipping to: {order.shipping_address}

Thank you for shopping with GadgetHub PH! 🇵🇭
"""

    send_email(
        subject    = f"✅ Order Confirmed – #{order_num} | GadgetHub PH",
        recipients = [user.email],
        html_body  = html,
        text_body  = plain,
    )