(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['shortcutHint'] = template({"compiler":[8,">= 4.3.0"],"main":function(container,depth0,helpers,partials,data) {
    var helper, lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return "<div id=\"shortcut-hint\">\n    <span class=\"audio-icon\"></span>\n    <kbd>"
    + container.escapeExpression(((helper = (helper = lookupProperty(helpers,"speak") || (depth0 != null ? lookupProperty(depth0,"speak") : depth0)) != null ? helper : container.hooks.helperMissing),(typeof helper === "function" ? helper.call(depth0 != null ? depth0 : (container.nullContext || {}),{"name":"speak","hash":{},"data":data,"loc":{"start":{"line":3,"column":9},"end":{"line":3,"column":18}}}) : helper)))
    + "</kbd>\n</div>";
},"useData":true});
})();