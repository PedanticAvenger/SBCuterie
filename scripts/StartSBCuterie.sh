
#!bin/sh

cd /home/pi/SBCuterie

sudo /etc/init.d/watchdog start &

. /home/pi/SBCuterie/SBCuterieWatchDog.sh&

while :
do

rm SBCuterie_Error.log

touch SBCuterie_Error.log

echo >> SBCuterie_Error.log
echo >> SBCuterie_Error.log
echo >> SBCuterie_Error.log
echo `date` >> SBCuterie_Error.log
echo >> SBCuterie_Error.log
echo "Starting Picuterie" >> SBCuterie_Error.log

echo "Charcuterie Curing Chamber Controller Started" | mail -s "SBCuterie Started" your_email_address@gmail.com

sudo python /home/pi/SBCuterie/SBCuterie.py 2>>SBCuterie_Error.log

echo "Charcuterie Curing Chamber Controller Crashed" | mail -s "SBCuterie Crashed" your_email_address@gmail.com < Picuterie_Error.log

sleep 60
done
