Working with wind
=================

Wind speed and direction describe different aspects of the same measurement.
Speed is a scalar; direction wraps at north. Choose the average that answers
your question before reducing either variable in time.

NOAA reports ``WDIR`` as the direction the wind comes from, clockwise from true
north. ``WSPD`` and gust speed ``GST`` use metres per second. See
`NOAA's measurement definitions <https://www.ndbc.noaa.gov/faq/measdes.shtml>`_
for station-dependent sampling conventions. xndbc preserves these measurements
without adjusting winds to a standard instrument height.

Inspect original observations
-----------------------------

.. code-block:: python

   import numpy as np
   import xndbc

   data = xndbc.historical("44013", years=2020)
   wind = data[["WSPD", "GST", "WDIR"]].sel(station_id="44013")
   wind.WSPD.plot.line(x="time")

For direction plots, points avoid drawing lines across the 0/360 boundary.
Exclude calm observations when interpreting wind direction. Inspect missing
values and sample counts before treating a daily summary as representative of
an entire day.

Mean speed and circular mean direction
--------------------------------------

An arithmetic mean describes average speed. Directions require a circular mean:
350 and 10 degrees point approximately north, while their arithmetic mean points
south. Average sine and cosine components of unit directions instead:

.. code-block:: python

   mean_speed = wind.WSPD.resample(time="D").mean(keep_attrs=True)
   angle = np.deg2rad(wind.WDIR.where(wind.WSPD > 0))
   sine = np.sin(angle).resample(time="D").mean()
   cosine = np.cos(angle).resample(time="D").mean()
   resultant = np.hypot(sine, cosine)
   mean_direction = (np.rad2deg(np.arctan2(sine, cosine)) % 360).where(
       resultant > 1e-12
   )

The resultant length measures directional agreement, from zero for cancellation
to one for identical directions. Mask a direction when the resultant is effectively
zero. Each valid direction contributes equally; this mean does not weight
observations by wind speed. These are sample means, which may differ from
means weighted by duration when sampling is irregular.

Mean wind vector
----------------

For average air motion, first convert speed and direction to eastward and
northward velocity. The minus signs convert the reported direction *from*
which the wind blows into the direction of motion. Use the same valid samples
for both components; calm measurements contribute zero even without a direction.

.. code-block:: python

   import xarray as xr

   angle = np.deg2rad(wind.WDIR)
   valid = wind.WSPD.notnull() & ((wind.WSPD == 0) | wind.WDIR.notnull())
   u = xr.where(wind.WSPD == 0, 0.0, -wind.WSPD * np.sin(angle)).where(valid)
   v = xr.where(wind.WSPD == 0, 0.0, -wind.WSPD * np.cos(angle)).where(valid)
   mean_u = u.resample(time="D").mean()
   mean_v = v.resample(time="D").mean()
   vector_speed = np.hypot(mean_u, mean_v)
   vector_direction = (np.rad2deg(np.arctan2(-mean_u, -mean_v)) % 360).where(
       vector_speed > 1e-12
   )

Opposing winds can cancel. The magnitude of the mean vector is therefore at most
the mean scalar speed calculated over the same samples. Its direction is undefined
when the magnitude is effectively zero.

Download the wind notebook from :doc:`examples` to compare these summaries with
plots and sample counts. Use the coverage guidance in :doc:`datasets` to assess
the observation window.
