
var since = new Date().getTime();
var interval = 3;
$(function() {
   if (GBrowserIsCompatible()) {
      var map = new GMap2(document.getElementById("map_canvas"));
      if ($('#id_start_place').val()=='uk')
          map.setCenter(new GLatLng(53.014783, -1.977539), 4); // uk
      else if ($('#id_start_place').val()=='us')
          map.setCenter(new GLatLng(41.804078, -97.954102), 4); // middle of us
      else
        map.setCenter(new GLatLng(28.921631, -17.226562), 4); // altantic ocean
      
      var info_window;
      function plot_new_searches(since) {
         $.getJSON('/crossing-the-world.json', {since:since}, function(res) {
            if (res.count >= 1) interval = 3;
            else interval += 0.2;
            $.each(res.items, function(i, item) {
               if (item.coordinates) {
                  var text = "Searched for '"+item.search_word.toUpperCase().replace(/ /g,'_')+"'";
                  if (item.found_word) {
                     text += "\nand found '" + item.found_word + "'!";
                     if (item.found_word_definition) {
                        text += "\n(which means: " + item.found_word_definition + ")";
                     }
                  }
                  map.panTo(new GLatLng(item.coordinates[1], item.coordinates[0]));
                  info_window = map.openInfoWindow(new GLatLng(item.coordinates[1], item.coordinates[0]),
						   document.createTextNode(text));
               }
            });
         });
      }
      
      function __start_plotting() {
         plot_new_searches(since);
         since = new Date().getTime();
         setTimeout(__start_plotting,  interval * 1000);
      }
      
      setTimeout(__start_plotting,  5*1000);
   }
});
