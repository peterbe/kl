function getLoading(context, bars, center, innerRadius, size, color) 
{
	var animating = true;
	var currentOffset = 0;
  
	function makeRGBA() 
	{
		return "rgba(" + [].slice.call(arguments, 0).join(",") + ")";
	}
	function drawBlock(ctx, barNo) 
	{
		ctx.fillStyle = makeRGBA(color.red, color.green, color.blue, (bars+1-barNo)/(bars+1));
		ctx.fillRect(-size.width/2, 0, size.width, size.height);
	}
	function calculateAngle(barNo) 
	{
		return 2 * barNo * Math.PI / bars;
	}
	function calculatePosition(barNo) 
	{
		angle = calculateAngle(barNo);
		return {
			y: (innerRadius * Math.cos(-angle)),
			x: (innerRadius * Math.sin(-angle)),
			angle: angle
		};
	}
	function draw(ctx, offset) 
	{
		clearFrame(ctx);
		ctx.save();

		ctx.translate(center.x, center.y);
		for(var i = 0; i<bars; i++)
		{
			var curbar = (offset+i) % bars,
				pos = calculatePosition(curbar);
			ctx.save();
			ctx.translate(pos.x, pos.y);
			ctx.rotate(pos.angle);
			drawBlock(context, i);
			ctx.restore();
		}
		ctx.restore();
	}
	function clearFrame(ctx) 
	{
		try{
			ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.width);
		}
		catch(e)
		{
			console.log(ctx.canvas.width);
		}
	}
	function nextAnimation()
	{
		if (!animating) {
			return;
		};
		currentOffset = (currentOffset + 1) % bars;
		draw(context, currentOffset);
		setTimeout(nextAnimation, 50);
	}
	nextAnimation(0);
	return {
		stop: function ()
		{
			animating = false;
			clearFrame(context);
		},
		start: function ()
		{
			animating = true;
			nextAnimation(0);
		},
		toggle: function ()
		{
			if(animating == true)
			{
				this.stop();
			}
			else 
			{
				this.start();
			}
		}
	};
}