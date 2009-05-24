
var since = new Date().getTime() - 10*1000; // start 10 seconds ago
var min_interval = 4;
var interval = min_interval;
$(function() {
   if (GBrowserIsCompatible()) {
      var map = new GMap2(document.getElementById("map_canvas"));
      map.addControl(new GLargeMapControl3D());
      
      var start_place = $('#id_start_place').val();
      if (start_place=='uk')
          map.setCenter(new GLatLng(53.014783, -1.977539), 4); // uk
      else if (start_place=='us')
          map.setCenter(new GLatLng(41.804078, -97.954102), 4); // middle of us
      else if (start_place=='fr')
          map.setCenter(new GLatLng(47.047669, 2.329102), 4); // middle of france
      else
        map.setCenter(new GLatLng(28.921631, -17.226562), 4); // altantic ocean
      
      var info_window;
      function plot_new_searches(since) {
         $.getJSON('/crossing-the-world.json', {since:since}, function(res) {
            if (res.count >= 1) interval = min_interval;
            else interval += 0.2;
            $.each(res.items, function(i, item) {
               if (item.coordinates) {
                  map.panTo(new GLatLng(item.coordinates[1], item.coordinates[0]));
                  info_window = map.openInfoWindowHtml(new GLatLng(item.coordinates[1], item.coordinates[0]),
                                                       item.text_html);
               }
            });
            if (res.search_rate) {
               $('#searches_rate_wrapper:hidden').show();
               $('#id_searches_rate').text(res.search_rate);
            }
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
