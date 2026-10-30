def register_views(app):

    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .data import ga_bp, issue_bp, onboard_bp, scrap_bp, site_bp
    from .master import bp as master_bp
    from .recruitment import bp as recruitment_bp

    for bp in (auth_bp, dashboard_bp, recruitment_bp, onboard_bp, ga_bp, scrap_bp, site_bp,
               issue_bp, master_bp):
        app.register_blueprint(bp)
