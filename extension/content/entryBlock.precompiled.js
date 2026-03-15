(function() {
  var template = Handlebars.template, templates = Handlebars.templates = Handlebars.templates || {};
templates['entryBlock'] = template({"1":function(container,depth0,helpers,partials,data) {
    var lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return "        <div class=\"phonetic\">"
    + container.escapeExpression((lookupProperty(helpers,"joinSyllables")||(depth0 && lookupProperty(depth0,"joinSyllables"))||container.hooks.helperMissing).call(depth0 != null ? depth0 : (container.nullContext || {}),(depth0 != null ? lookupProperty(depth0,"roman") : depth0),{"name":"joinSyllables","hash":{},"data":data,"loc":{"start":{"line":3,"column":30},"end":{"line":3,"column":53}}}))
    + "</div>\n";
},"3":function(container,depth0,helpers,partials,data,blockParams,depths) {
    var stack1, alias1=depth0 != null ? depth0 : (container.nullContext || {}), alias2=container.hooks.helperMissing, lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return ((stack1 = lookupProperty(helpers,"if").call(alias1,(depth0 != null ? lookupProperty(depth0,"classifier") : depth0),{"name":"if","hash":{},"fn":container.program(4, data, 0, blockParams, depths),"inverse":container.noop,"data":data,"loc":{"start":{"line":7,"column":12},"end":{"line":15,"column":19}}})) != null ? stack1 : "")
    + "            <span class=\"sense "
    + ((stack1 = lookupProperty(helpers,"if").call(alias1,(lookupProperty(helpers,"eq")||(depth0 && lookupProperty(depth0,"eq"))||alias2).call(alias1,((stack1 = (depths[1] != null ? lookupProperty(depths[1],"glosses") : depths[1])) != null ? lookupProperty(stack1,"length") : stack1),1,{"name":"eq","hash":{},"data":data,"loc":{"start":{"line":16,"column":37},"end":{"line":16,"column":61}}}),{"name":"if","hash":{},"fn":container.program(10, data, 0, blockParams, depths),"inverse":container.noop,"data":data,"loc":{"start":{"line":16,"column":31},"end":{"line":16,"column":76}}})) != null ? stack1 : "")
    + "\">\n"
    + ((stack1 = lookupProperty(helpers,"if").call(alias1,(depth0 != null ? lookupProperty(depth0,"pos") : depth0),{"name":"if","hash":{},"fn":container.program(12, data, 0, blockParams, depths),"inverse":container.noop,"data":data,"loc":{"start":{"line":17,"column":16},"end":{"line":19,"column":23}}})) != null ? stack1 : "")
    + ((stack1 = lookupProperty(helpers,"each").call(alias1,(depth0 != null ? lookupProperty(depth0,"tags") : depth0),{"name":"each","hash":{},"fn":container.program(14, data, 0, blockParams, depths),"inverse":container.noop,"data":data,"loc":{"start":{"line":20,"column":16},"end":{"line":22,"column":25}}})) != null ? stack1 : "")
    + "                "
    + ((stack1 = (lookupProperty(helpers,"spanifyThai")||(depth0 && lookupProperty(depth0,"spanifyThai"))||alias2).call(alias1,(depth0 != null ? lookupProperty(depth0,"en") : depth0),{"name":"spanifyThai","hash":{},"data":data,"loc":{"start":{"line":23,"column":16},"end":{"line":23,"column":36}}})) != null ? stack1 : "")
    + "\n            </span>\n";
},"4":function(container,depth0,helpers,partials,data) {
    var stack1, alias1=depth0 != null ? depth0 : (container.nullContext || {}), lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return "                <span class=\"classifier\">\n                    [<em>classifier"
    + ((stack1 = lookupProperty(helpers,"if").call(alias1,(lookupProperty(helpers,"gt")||(depth0 && lookupProperty(depth0,"gt"))||container.hooks.helperMissing).call(alias1,((stack1 = (depth0 != null ? lookupProperty(depth0,"classifier") : depth0)) != null ? lookupProperty(stack1,"length") : stack1),1,{"name":"gt","hash":{},"data":data,"loc":{"start":{"line":9,"column":41},"end":{"line":9,"column":65}}}),{"name":"if","hash":{},"fn":container.program(5, data, 0),"inverse":container.noop,"data":data,"loc":{"start":{"line":9,"column":35},"end":{"line":9,"column":75}}})) != null ? stack1 : "")
    + ":</em> \n"
    + ((stack1 = lookupProperty(helpers,"each").call(alias1,(depth0 != null ? lookupProperty(depth0,"classifier") : depth0),{"name":"each","hash":{},"fn":container.program(7, data, 0),"inverse":container.noop,"data":data,"loc":{"start":{"line":10,"column":20},"end":{"line":13,"column":59}}})) != null ? stack1 : "")
    + "]\n                </span>\n";
},"5":function(container,depth0,helpers,partials,data) {
    return "s";
},"7":function(container,depth0,helpers,partials,data) {
    var stack1, helper, alias1=depth0 != null ? depth0 : (container.nullContext || {}), alias2=container.hooks.helperMissing, alias3="function", alias4=container.escapeExpression, lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return "                        "
    + ((stack1 = lookupProperty(helpers,"if").call(alias1,(data && lookupProperty(data,"index")),{"name":"if","hash":{},"fn":container.program(8, data, 0),"inverse":container.noop,"data":data,"loc":{"start":{"line":11,"column":24},"end":{"line":11,"column":47}}})) != null ? stack1 : "")
    + "\n                        <span lang=\"th\">"
    + alias4(((helper = (helper = lookupProperty(helpers,"thai") || (depth0 != null ? lookupProperty(depth0,"thai") : depth0)) != null ? helper : alias2),(typeof helper === alias3 ? helper.call(alias1,{"name":"thai","hash":{},"data":data,"loc":{"start":{"line":12,"column":40},"end":{"line":12,"column":48}}}) : helper)))
    + "</span>\n                        <strong>"
    + alias4(((helper = (helper = lookupProperty(helpers,"roman") || (depth0 != null ? lookupProperty(depth0,"roman") : depth0)) != null ? helper : alias2),(typeof helper === alias3 ? helper.call(alias1,{"name":"roman","hash":{},"data":data,"loc":{"start":{"line":13,"column":32},"end":{"line":13,"column":41}}}) : helper)))
    + "</strong>";
},"8":function(container,depth0,helpers,partials,data) {
    return ", ";
},"10":function(container,depth0,helpers,partials,data) {
    return "single";
},"12":function(container,depth0,helpers,partials,data) {
    var helper, lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return "                    <span class=\"pos\">"
    + container.escapeExpression(((helper = (helper = lookupProperty(helpers,"pos") || (depth0 != null ? lookupProperty(depth0,"pos") : depth0)) != null ? helper : container.hooks.helperMissing),(typeof helper === "function" ? helper.call(depth0 != null ? depth0 : (container.nullContext || {}),{"name":"pos","hash":{},"data":data,"loc":{"start":{"line":18,"column":38},"end":{"line":18,"column":45}}}) : helper)))
    + "</span>\n";
},"14":function(container,depth0,helpers,partials,data) {
    return "                    <span class=\"tag\">"
    + container.escapeExpression(container.lambda(depth0, depth0))
    + "</span>\n";
},"compiler":[8,">= 4.3.0"],"main":function(container,depth0,helpers,partials,data,blockParams,depths) {
    var stack1, alias1=depth0 != null ? depth0 : (container.nullContext || {}), lookupProperty = container.lookupProperty || function(parent, propertyName) {
        if (Object.prototype.hasOwnProperty.call(parent, propertyName)) {
          return parent[propertyName];
        }
        return undefined
    };

  return "<div class=\"entry\">\n"
    + ((stack1 = lookupProperty(helpers,"if").call(alias1,(depth0 != null ? lookupProperty(depth0,"roman") : depth0),{"name":"if","hash":{},"fn":container.program(1, data, 0, blockParams, depths),"inverse":container.noop,"data":data,"loc":{"start":{"line":2,"column":4},"end":{"line":4,"column":11}}})) != null ? stack1 : "")
    + "    <div class=\"senses\">\n"
    + ((stack1 = lookupProperty(helpers,"each").call(alias1,(depth0 != null ? lookupProperty(depth0,"glosses") : depth0),{"name":"each","hash":{},"fn":container.program(3, data, 0, blockParams, depths),"inverse":container.noop,"data":data,"loc":{"start":{"line":6,"column":8},"end":{"line":25,"column":17}}})) != null ? stack1 : "")
    + "    </div>\n</div>";
},"useData":true,"useDepths":true});
})();