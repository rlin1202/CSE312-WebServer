import util.response
import util.request

class Router:

    def __init__(self):
        self.routes = []
        pass

    def add_route(self, method, path, action, exact_path=False):
        self.routes.append((method,path,action,exact_path))
        pass

    def route_request(self, request, handler):
        # route request steps
        # first check method
        # if they match move on to check path and the exact path
        # if everything matches up save the function and call the function assocaited with route
        # if nothing found then return a 404 not found response.
        for method, routePath, action, exact_path in self.routes:
            if method == request.method:
                # if route found call method, after method call exit and return
                if exact_path == True:
                    if request.path == routePath:
                        action(request, handler)
                        return
                else:
                    if request.path.startswith(routePath):
                        action(request, handler)
                        return
        response = util.response.Response()
        response.set_status(404,"Not Found")
        response.text("Route Not Found")
        handler.request.sendall(response.to_data())
