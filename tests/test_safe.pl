use Safe;
$compartment = new Safe;
$compartment->permit(qw(time sort :browse));
my $unsafe_code = <<'UNSAFE_CODE';
print "hello";
UNSAFE_CODE
$result = $compartment->reval($unsafe_code);
if($@){
    print $@;
}else{
    print $result;
}