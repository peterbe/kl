
var since = new Date().getTime();

$(function() {
   if (GBrowserIsCompatible()) {
      var map = new GMap2(document.getElementById("map_canvas"));
      if ($('#id_start_place').val()=='uk')
          map.setCenter(new GLatLng(53.014783, -1.977539), 4); // uk
      else if ($('#id_start_place').val()=='us')
          map.setCenter(new GLatLng(41.804078, -97.954102), 4); // middle of us
      else
        map.setCenter(new GLatLng(28.921631, -17.226562), 4); // altantic ocean
      
      var info_windows = new Array();
      function plot_new_searches(since) {
         $.getJSON('/crossing-the-world.json', {since:since}, function(res) {
            $.each(res, function(i, item) {
               //console.log(item);
               if (item.coordinates) {
                  map.setCenter(new GLatLng(item.coordinates[1], item.coordinates[0]));
                  info_windows.push(map.openInfoWindow(new GLatLng(item.coordinates[1], item.coordinates[0]),
                                                       document.createTextNode(item.search_word.toUpperCase().replace(' ','_'))));
               }
            });
         });
      }
      
      function __start_plotting() {
         plot_new_searches(since);
         since = new Date().getTime();
         setTimeout(__start_plotting,  5*1000);
      }
      
      setTimeout(__start_plotting,  5*1000);
   }
});
