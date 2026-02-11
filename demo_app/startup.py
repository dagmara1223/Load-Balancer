from sqlalchemy import create_engine
from config.config_loader import ConfigLoader
from connection.engine_factory import EngineFactory
from load_balancer.load_balancer import LoadBalancer


def init_app():
    # load DB configuration
    cfg = ConfigLoader("config/database_config.yaml")

    # create engines for all configured nodes 
    ef = EngineFactory(cfg)
    engines = ef.create_engines()
    print(f"Created engines: {list(engines.keys())}")

    # register engines with load balancer
    lb = LoadBalancer()
    ef.register_with_load_balancer(lb)
    print("Registered engines with LoadBalancer")

    # create a fronting engine that the application will use directly
    # the listener will intercept calls on this engine and forward/broadcast
    frontend_engine = create_engine("sqlite:///:memory:", echo=False, future=True)


    return {
        "config_loader": cfg,
        "engine_factory": ef,
        "engines": engines,
        "load_balancer": lb,
        "frontend_engine": frontend_engine,
    }


if __name__ == "__main__":
    init_app()
    print("Startup complete")
