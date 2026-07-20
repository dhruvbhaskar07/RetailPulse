"""Dashboard page modules."""
from src.dashboard.pages.overview     import render as overview_render
from src.dashboard.pages.forecast     import render as forecast_render
from src.dashboard.pages.segments     import render as segments_render
from src.dashboard.pages.churn        import render as churn_render
from src.dashboard.pages.inventory    import render as inventory_render
from src.dashboard.pages.simulator    import render as simulator_render
from src.dashboard.pages.drift        import render as drift_render
from src.dashboard.pages.models       import render as models_render
from src.dashboard.pages.import_data  import render as import_render

PAGE_RENDERERS = {
    "Overview":  overview_render,
    "Forecast":  forecast_render,
    "Segments":  segments_render,
    "Churn":     churn_render,
    "Inventory": inventory_render,
    "Simulator": simulator_render,
    "Drift":     drift_render,
    "Models":    models_render,
    "Import":    import_render,
}