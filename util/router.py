import util.response
import util.request

class Router:

    def __init__(self):
        self.routes = []
        pass

    def add_route(self, method, path, action, exact_path=False):
        self.routes.append([method,path,action,exact_path])
        pass

    def route_request(self, request, handler):
        for route in self.routes:
            # idea check if method and path match, if they do call the function associated with route
            # check exact path before checking method and path match????
            # if exact path is default false then match with start with

            if request.method == self.routes[route][0] and request.path == self.routes[route][1]:
                route_function = self.routes[route][2]
                route_function(request,handler)

        pass
