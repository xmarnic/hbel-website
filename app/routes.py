from flask import current_app, flash, redirect, render_template, request, send_from_directory, url_for

from .mail import send_contact_email

MAX_MESSAGE_LENGTH = 5000


def register_routes(app):
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/services")
    def services():
        from .services_data import SERVICES

        return render_template("services.html", services=SERVICES)

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "GET":
            return render_template("contact.html")

        form = request.form
        name = form.get("name", "").strip()
        email = form.get("email", "").strip()
        message = form.get("message", "").strip()
        honeypot = form.get("website", "").strip()

        if honeypot:
            flash("Thanks for reaching out! We'll be in touch soon.", "success")
            return redirect(url_for("contact"))

        errors = []
        if not name:
            errors.append("Please enter your name.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email address.")
        if not message:
            errors.append("Please enter a message.")
        elif len(message) > MAX_MESSAGE_LENGTH:
            errors.append("Message is too long.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "contact.html", name=name, email=email, message=message
            )

        try:
            send_contact_email(
                name=name,
                email=email,
                message=message,
                config=current_app.config,
            )
        except Exception:
            current_app.logger.exception("Failed to send contact email")
            flash(
                "Sorry, something went wrong sending your message. "
                "Please try emailing us directly instead.",
                "error",
            )
            return render_template(
                "contact.html", name=name, email=email, message=message
            )

        flash("Thanks for reaching out! We'll be in touch soon.", "success")
        return redirect(url_for("contact"))

    @app.route("/robots.txt")
    def robots_txt():
        return send_from_directory(
            current_app.static_folder, "robots.txt", mimetype="text/plain"
        )

    @app.route("/sitemap.xml")
    def sitemap_xml():
        return send_from_directory(
            current_app.static_folder, "sitemap.xml", mimetype="application/xml"
        )

    @app.route("/services-store/")
    @app.route("/services-store/<path:subpath>")
    def services_store_redirect(subpath=None):
        return redirect(url_for("services"), code=301)

    @app.route("/cart")
    def cart_redirect():
        return redirect(url_for("contact"), code=301)
