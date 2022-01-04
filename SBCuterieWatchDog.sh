echo "Starting Softdog"

touch /home/pi/SBCuterie/SBCuterie.softdog

while :
do

if test `find "/home/pi/SBCuterie/SBCuterie.softdog" -amin +10`
then
echo "Charcuterie Curing Chamber Controller Softdog Stopped" | mail -s "SBCuterie Softdog Stopped - Rebooting" your_email_address@gmail.com < SBCuterie_Error.log
sudo shutdown -r now
fi

sudo python /home/pi/SBCuterie/SBCuterieCheckEmail.py

sleep 10m
done
